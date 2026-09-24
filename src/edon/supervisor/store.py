"""Immutable custody store for shadow-supervisor cycles."""

from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from edon.common.hashing import canonical_json, sha256_json


class SupervisorError(RuntimeError):
    """Raised when a shadow-cycle identity or custody invariant is violated."""


class ShadowCycleStore:
    def __init__(self, path: Path | str):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA journal_mode = WAL")
        return connection

    @contextmanager
    def _connection(self):
        connection = self._connect()
        try:
            with connection:
                yield connection
        finally:
            connection.close()

    def _initialize(self) -> None:
        with self._connection() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS shadow_cycles (
                    cycle_id TEXT PRIMARY KEY,
                    tenant_id TEXT NOT NULL,
                    world_id TEXT NOT NULL,
                    world_version INTEGER NOT NULL,
                    world_state_sha256 TEXT NOT NULL,
                    context_sha256 TEXT NOT NULL,
                    proposal_json TEXT NOT NULL,
                    proposal_sha256 TEXT NOT NULL,
                    request_sha256 TEXT NOT NULL,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                CREATE TRIGGER IF NOT EXISTS shadow_cycles_no_update
                BEFORE UPDATE ON shadow_cycles BEGIN
                    SELECT RAISE(ABORT, 'shadow cycles are immutable');
                END;
                CREATE TRIGGER IF NOT EXISTS shadow_cycles_no_delete
                BEFORE DELETE ON shadow_cycles BEGIN
                    SELECT RAISE(ABORT, 'shadow cycles are immutable');
                END;
                """
            )
        self.path.chmod(0o600)

    @staticmethod
    def _row(row: sqlite3.Row) -> dict[str, Any]:
        return {
            "cycle_id": row["cycle_id"],
            "tenant_id": row["tenant_id"],
            "world_id": row["world_id"],
            "world_version": row["world_version"],
            "world_state_sha256": row["world_state_sha256"],
            "context_sha256": row["context_sha256"],
            "proposal": json.loads(row["proposal_json"]),
            "proposal_sha256": row["proposal_sha256"],
            "status": row["status"],
            "created_at": row["created_at"],
            "binding_authority": False,
        }

    def record(self, cycle: dict[str, Any], *, timestamp: str | None = None) -> dict[str, Any]:
        cycle_id = str(cycle.get("cycle_id", "")).strip()
        if not cycle_id:
            raise SupervisorError("cycle_id is required")
        created_at = timestamp or datetime.now(UTC).isoformat()
        request_hash = sha256_json(cycle)
        with self._connection() as connection:
            existing = connection.execute(
                "SELECT * FROM shadow_cycles WHERE cycle_id = ?", (cycle_id,)
            ).fetchone()
            if existing:
                if existing["request_sha256"] != request_hash:
                    raise SupervisorError("cycle identity is already bound to different content")
                return self._row(existing)
            connection.execute(
                """INSERT INTO shadow_cycles
                   (cycle_id, tenant_id, world_id, world_version, world_state_sha256,
                    context_sha256, proposal_json, proposal_sha256, request_sha256,
                    status, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'SHADOW_ONLY', ?)""",
                (
                    cycle_id, cycle["tenant_id"], cycle["world_id"], cycle["world_version"],
                    cycle["world_state_sha256"], cycle["context_sha256"],
                    canonical_json(cycle["proposal"]), cycle["proposal"]["proposal_sha256"],
                    request_hash, created_at,
                ),
            )
            row = connection.execute(
                "SELECT * FROM shadow_cycles WHERE cycle_id = ?", (cycle_id,)
            ).fetchone()
        assert row is not None
        return self._row(row)

    def list_cycles(self, tenant_id: str, world_id: str) -> list[dict[str, Any]]:
        with self._connection() as connection:
            return [
                self._row(row)
                for row in connection.execute(
                    """SELECT * FROM shadow_cycles WHERE tenant_id = ? AND world_id = ?
                       ORDER BY created_at, cycle_id""",
                    (tenant_id, world_id),
                )
            ]

    def count_cycles(self) -> int:
        with self._connection() as connection:
            return int(connection.execute("SELECT COUNT(*) FROM shadow_cycles").fetchone()[0])