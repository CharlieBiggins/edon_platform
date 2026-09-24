"""Tenant-isolated, provenance-bearing episodic memory with immutable audit."""

from __future__ import annotations

import json
import re
import sqlite3
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Iterable

from edon.common.hashing import canonical_json, sha256_json, sha256_text


class MemoryStoreError(RuntimeError):
    """Raised when memory custody, access, or provenance rules are violated."""


SENSITIVITIES = {"PUBLIC", "INTERNAL", "CONFIDENTIAL", "RESTRICTED"}
TOKEN_RE = re.compile(r"[a-z0-9_:@.-]+")


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _identifier(value: str, label: str) -> str:
    normalized = str(value).strip()
    if not normalized or len(normalized) > 200:
        raise MemoryStoreError(f"{label} must contain between 1 and 200 characters")
    return normalized


def _parse_time(value: str, label: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise MemoryStoreError(f"{label} must be an ISO-8601 timestamp") from exc
    if parsed.tzinfo is None:
        raise MemoryStoreError(f"{label} must include a timezone")
    return parsed.astimezone(UTC)


def _tokens(value: str) -> set[str]:
    return set(TOKEN_RE.findall(value.lower()))


class EpisodicMemoryStore:
    """Immutable episodes plus tombstones and hash-chained access records."""

    def __init__(self, path: Path | str):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
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
                CREATE TABLE IF NOT EXISTS memory_entries (
                    tenant_id TEXT NOT NULL,
                    memory_id TEXT NOT NULL,
                    world_id TEXT NOT NULL,
                    episode_type TEXT NOT NULL,
                    summary TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    occurred_at TEXT NOT NULL,
                    sensitivity TEXT NOT NULL,
                    retention_until TEXT,
                    source_event_ids_json TEXT NOT NULL,
                    provenance_json TEXT NOT NULL,
                    content_sha256 TEXT NOT NULL,
                    created_by TEXT NOT NULL,
                    authorization_ref TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    PRIMARY KEY (tenant_id, memory_id)
                );
                CREATE TABLE IF NOT EXISTS memory_tombstones (
                    tenant_id TEXT NOT NULL,
                    memory_id TEXT NOT NULL,
                    reason TEXT NOT NULL,
                    actor_id TEXT NOT NULL,
                    authorization_ref TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    PRIMARY KEY (tenant_id, memory_id),
                    FOREIGN KEY (tenant_id, memory_id) REFERENCES memory_entries(tenant_id, memory_id)
                );
                CREATE TABLE IF NOT EXISTS memory_audit (
                    sequence INTEGER PRIMARY KEY AUTOINCREMENT,
                    tenant_id TEXT NOT NULL,
                    action TEXT NOT NULL,
                    memory_id TEXT NOT NULL,
                    actor_id TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    previous_hash TEXT NOT NULL,
                    audit_hash TEXT NOT NULL UNIQUE,
                    created_at TEXT NOT NULL
                );
                CREATE TRIGGER IF NOT EXISTS memory_entries_no_update
                BEFORE UPDATE ON memory_entries BEGIN
                    SELECT RAISE(ABORT, 'memory entries are immutable');
                END;
                CREATE TRIGGER IF NOT EXISTS memory_entries_no_delete
                BEFORE DELETE ON memory_entries BEGIN
                    SELECT RAISE(ABORT, 'memory entries are immutable');
                END;
                CREATE TRIGGER IF NOT EXISTS memory_tombstones_no_update
                BEFORE UPDATE ON memory_tombstones BEGIN
                    SELECT RAISE(ABORT, 'memory tombstones are immutable');
                END;
                CREATE TRIGGER IF NOT EXISTS memory_tombstones_no_delete
                BEFORE DELETE ON memory_tombstones BEGIN
                    SELECT RAISE(ABORT, 'memory tombstones are immutable');
                END;
                CREATE TRIGGER IF NOT EXISTS memory_audit_no_update
                BEFORE UPDATE ON memory_audit BEGIN
                    SELECT RAISE(ABORT, 'memory audit events are immutable');
                END;
                CREATE TRIGGER IF NOT EXISTS memory_audit_no_delete
                BEFORE DELETE ON memory_audit BEGIN
                    SELECT RAISE(ABORT, 'memory audit events are immutable');
                END;
                """
            )
        self.path.chmod(0o600)

    def _append_audit(
        self,
        connection: sqlite3.Connection,
        tenant_id: str,
        action: str,
        memory_id: str,
        actor_id: str,
        payload: dict[str, Any],
        created_at: str,
    ) -> str:
        previous = connection.execute(
            "SELECT audit_hash FROM memory_audit WHERE tenant_id = ? ORDER BY sequence DESC LIMIT 1",
            (tenant_id,),
        ).fetchone()
        previous_hash = previous["audit_hash"] if previous else "GENESIS"
        event = {
            "tenant_id": tenant_id,
            "action": action,
            "memory_id": memory_id,
            "actor_id": actor_id,
            "payload": payload,
            "previous_hash": previous_hash,
            "created_at": created_at,
        }
        audit_hash = sha256_json(event)
        connection.execute(
            """INSERT INTO memory_audit
               (tenant_id, action, memory_id, actor_id, payload_json, previous_hash, audit_hash, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                tenant_id, action, memory_id, actor_id, canonical_json(payload),
                previous_hash, audit_hash, created_at,
            ),
        )
        return audit_hash

    @staticmethod
    def _entry(row: sqlite3.Row, *, score: int | None = None) -> dict[str, Any]:
        result = {
            "schema_version": "edon-episodic-memory.v1",
            "tenant_id": row["tenant_id"],
            "memory_id": row["memory_id"],
            "world_id": row["world_id"],
            "episode_type": row["episode_type"],
            "summary": row["summary"],
            "payload": json.loads(row["payload_json"]),
            "occurred_at": row["occurred_at"],
            "sensitivity": row["sensitivity"],
            "retention_until": row["retention_until"],
            "source_event_ids": json.loads(row["source_event_ids_json"]),
            "provenance": json.loads(row["provenance_json"]),
            "content_sha256": row["content_sha256"],
            "created_by": row["created_by"],
            "created_at": row["created_at"],
            "scope": "INSTITUTION_LOCAL",
            "adaptation_mode": "CONTEXT_ONLY",
            "training_eligible": False,
            "weight_update_authorized": False,
            "binding_authority": False,
        }
        if score is not None:
            result["retrieval_score"] = score
        return result

    def record_episode(
        self,
        tenant_id: str,
        memory_id: str,
        world_id: str,
        episode_type: str,
        summary: str,
        payload: dict[str, Any],
        *,
        occurred_at: str,
        sensitivity: str,
        actor_id: str,
        authorization_ref: str,
        source_event_ids: Iterable[str] = (),
        provenance: dict[str, Any] | None = None,
        retention_until: str | None = None,
        timestamp: str | None = None,
    ) -> dict[str, Any]:
        tenant_id = _identifier(tenant_id, "tenant_id")
        memory_id = _identifier(memory_id, "memory_id")
        world_id = _identifier(world_id, "world_id")
        episode_type = _identifier(episode_type, "episode_type")
        actor_id = _identifier(actor_id, "actor_id")
        authorization_ref = _identifier(authorization_ref, "authorization_ref")
        summary = str(summary).strip()
        if len(summary) < 10 or len(summary) > 10_000:
            raise MemoryStoreError("summary must contain between 10 and 10000 characters")
        if not isinstance(payload, dict):
            raise MemoryStoreError("memory payload must be a JSON object")
        if not isinstance(provenance or {}, dict):
            raise MemoryStoreError("provenance must be a JSON object")
        try:
            json.dumps(payload, allow_nan=False)
            json.dumps(provenance or {}, allow_nan=False)
        except (TypeError, ValueError) as exc:
            raise MemoryStoreError("memory payload and provenance must be finite JSON") from exc
        occurred = _parse_time(occurred_at, "occurred_at").isoformat()
        retained = _parse_time(retention_until, "retention_until").isoformat() if retention_until else None
        if retained and _parse_time(retained, "retention_until") < _parse_time(occurred, "occurred_at"):
            raise MemoryStoreError("retention_until cannot precede occurred_at")
        sensitivity = str(sensitivity).upper()
        if sensitivity not in SENSITIVITIES:
            raise MemoryStoreError(f"unsupported sensitivity: {sensitivity}")
        sources = sorted({_identifier(item, "source event id") for item in source_event_ids})
        provenance = dict(provenance or {})
        if not sources and not provenance:
            raise MemoryStoreError("memory requires source_event_ids or provenance")
        created_at = timestamp or _now()
        content = {
            "tenant_id": tenant_id,
            "memory_id": memory_id,
            "world_id": world_id,
            "episode_type": episode_type,
            "summary": summary,
            "payload": payload,
            "occurred_at": occurred,
            "sensitivity": sensitivity,
            "retention_until": retained,
            "source_event_ids": sources,
            "provenance": provenance,
            "created_by": actor_id,
            "authorization_ref": authorization_ref,
        }
        content_hash = sha256_json(content)
        with self._connection() as connection:
            connection.execute("BEGIN IMMEDIATE")
            existing = connection.execute(
                "SELECT * FROM memory_entries WHERE tenant_id = ? AND memory_id = ?",
                (tenant_id, memory_id),
            ).fetchone()
            if existing:
                if existing["content_sha256"] != content_hash:
                    raise MemoryStoreError("memory identity is already bound to different content")
                return self._entry(existing)
            connection.execute(
                """INSERT INTO memory_entries
                   (tenant_id, memory_id, world_id, episode_type, summary, payload_json,
                    occurred_at, sensitivity, retention_until, source_event_ids_json,
                    provenance_json, content_sha256, created_by, authorization_ref, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    tenant_id, memory_id, world_id, episode_type, summary,
                    canonical_json(payload), occurred, sensitivity, retained,
                    canonical_json(sources), canonical_json(provenance), content_hash,
                    actor_id, authorization_ref, created_at,
                ),
            )
            self._append_audit(
                connection,
                tenant_id,
                "MEMORY_RECORDED",
                memory_id,
                actor_id,
                {
                    "world_id": world_id,
                    "episode_type": episode_type,
                    "sensitivity": sensitivity,
                    "content_sha256": content_hash,
                    "source_event_ids": sources,
                },
                created_at,
            )
            row = connection.execute(
                "SELECT * FROM memory_entries WHERE tenant_id = ? AND memory_id = ?",
                (tenant_id, memory_id),
            ).fetchone()
        assert row is not None
        return self._entry(row)

    def get_episode(
        self,
        tenant_id: str,
        memory_id: str,
        *,
        actor_id: str,
        allowed_sensitivities: Iterable[str],
        as_of: str | None = None,
        timestamp: str | None = None,
    ) -> dict[str, Any]:
        tenant_id = _identifier(tenant_id, "tenant_id")
        memory_id = _identifier(memory_id, "memory_id")
        actor_id = _identifier(actor_id, "actor_id")
        allowed = {str(item).upper() for item in allowed_sensitivities}
        if not allowed or not allowed.issubset(SENSITIVITIES):
            raise MemoryStoreError("allowed_sensitivities must contain registered sensitivity values")
        current_time = _parse_time(as_of, "as_of") if as_of else datetime.now(UTC)
        created_at = timestamp or _now()
        with self._connection() as connection:
            row = connection.execute(
                """SELECT e.* FROM memory_entries e
                   LEFT JOIN memory_tombstones t
                     ON t.tenant_id = e.tenant_id AND t.memory_id = e.memory_id
                   WHERE e.tenant_id = ? AND e.memory_id = ? AND t.memory_id IS NULL""",
                (tenant_id, memory_id),
            ).fetchone()
            if not row or row["sensitivity"] not in allowed:
                raise MemoryStoreError("memory not found or access denied")
            if row["retention_until"] and _parse_time(row["retention_until"], "retention_until") < current_time:
                raise MemoryStoreError("memory not found or access denied")
            self._append_audit(
                connection,
                tenant_id,
                "MEMORY_READ",
                memory_id,
                actor_id,
                {"sensitivity": row["sensitivity"], "content_sha256": row["content_sha256"]},
                created_at,
            )
            return self._entry(row)

    def query(
        self,
        tenant_id: str,
        query: str,
        *,
        actor_id: str,
        allowed_sensitivities: Iterable[str],
        world_id: str | None = None,
        episode_types: Iterable[str] = (),
        limit: int = 20,
        as_of: str | None = None,
        timestamp: str | None = None,
    ) -> list[dict[str, Any]]:
        tenant_id = _identifier(tenant_id, "tenant_id")
        actor_id = _identifier(actor_id, "actor_id")
        world_id = _identifier(world_id, "world_id") if world_id is not None else None
        allowed = {str(item).upper() for item in allowed_sensitivities}
        if not allowed or not allowed.issubset(SENSITIVITIES):
            raise MemoryStoreError("allowed_sensitivities must contain registered sensitivity values")
        types = {_identifier(item, "episode type") for item in episode_types}
        limit = int(limit)
        if limit < 1 or limit > 200:
            raise MemoryStoreError("memory query limit must be between 1 and 200")
        current_time = _parse_time(as_of, "as_of") if as_of else datetime.now(UTC)
        query_tokens = _tokens(str(query))
        created_at = timestamp or _now()
        with self._connection() as connection:
            rows = list(connection.execute(
                """SELECT e.* FROM memory_entries e
                   LEFT JOIN memory_tombstones t
                     ON t.tenant_id = e.tenant_id AND t.memory_id = e.memory_id
                   WHERE e.tenant_id = ? AND t.memory_id IS NULL""",
                (tenant_id,),
            ))
            scored: list[tuple[int, str, str, sqlite3.Row]] = []
            for row in rows:
                if row["sensitivity"] not in allowed:
                    continue
                if world_id is not None and row["world_id"] != world_id:
                    continue
                if types and row["episode_type"] not in types:
                    continue
                if row["retention_until"] and _parse_time(row["retention_until"], "retention_until") < current_time:
                    continue
                document = " ".join((row["summary"], row["episode_type"], row["payload_json"]))
                score = len(query_tokens & _tokens(document)) if query_tokens else 0
                if query_tokens and score == 0:
                    continue
                scored.append((score, row["occurred_at"], row["memory_id"], row))
            scored.sort(
                key=lambda item: (
                    -item[0],
                    -_parse_time(item[1], "occurred_at").timestamp(),
                    item[2],
                )
            )
            selected = scored[:limit]
            self._append_audit(
                connection,
                tenant_id,
                "MEMORY_QUERY",
                "QUERY",
                actor_id,
                {
                    "query_sha256": sha256_text(str(query)),
                    "world_id": world_id,
                    "episode_types": sorted(types),
                    "allowed_sensitivities": sorted(allowed),
                    "result_count": len(selected),
                },
                created_at,
            )
        return [self._entry(row, score=score) for score, _, _, row in selected]

    def tombstone(
        self,
        tenant_id: str,
        memory_id: str,
        *,
        actor_id: str,
        reason: str,
        authorization_ref: str,
        timestamp: str | None = None,
    ) -> dict[str, Any]:
        tenant_id = _identifier(tenant_id, "tenant_id")
        memory_id = _identifier(memory_id, "memory_id")
        actor_id = _identifier(actor_id, "actor_id")
        authorization_ref = _identifier(authorization_ref, "authorization_ref")
        reason = str(reason).strip()
        if len(reason) < 5:
            raise MemoryStoreError("tombstone reason must be explicit")
        created_at = timestamp or _now()
        with self._connection() as connection:
            connection.execute("BEGIN IMMEDIATE")
            entry = connection.execute(
                "SELECT content_sha256 FROM memory_entries WHERE tenant_id = ? AND memory_id = ?",
                (tenant_id, memory_id),
            ).fetchone()
            if not entry:
                raise MemoryStoreError("memory not found for tenant")
            existing = connection.execute(
                "SELECT * FROM memory_tombstones WHERE tenant_id = ? AND memory_id = ?",
                (tenant_id, memory_id),
            ).fetchone()
            if existing:
                return {
                    "tenant_id": tenant_id,
                    "memory_id": memory_id,
                    "status": "TOMBSTONED",
                    "created_at": existing["created_at"],
                }
            connection.execute(
                """INSERT INTO memory_tombstones
                   (tenant_id, memory_id, reason, actor_id, authorization_ref, created_at)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (tenant_id, memory_id, reason, actor_id, authorization_ref, created_at),
            )
            self._append_audit(
                connection,
                tenant_id,
                "MEMORY_TOMBSTONED",
                memory_id,
                actor_id,
                {
                    "reason": reason,
                    "authorization_ref": authorization_ref,
                    "content_sha256": entry["content_sha256"],
                },
                created_at,
            )
        return {
            "tenant_id": tenant_id,
            "memory_id": memory_id,
            "status": "TOMBSTONED",
            "created_at": created_at,
        }

    def audit_events(self, tenant_id: str) -> list[dict[str, Any]]:
        tenant_id = _identifier(tenant_id, "tenant_id")
        with self._connection() as connection:
            return [
                {
                    "sequence": row["sequence"],
                    "tenant_id": row["tenant_id"],
                    "action": row["action"],
                    "memory_id": row["memory_id"],
                    "actor_id": row["actor_id"],
                    "payload": json.loads(row["payload_json"]),
                    "previous_hash": row["previous_hash"],
                    "audit_hash": row["audit_hash"],
                    "created_at": row["created_at"],
                }
                for row in connection.execute(
                    "SELECT * FROM memory_audit WHERE tenant_id = ? ORDER BY sequence", (tenant_id,)
                )
            ]

    def verify_audit_chain(self, tenant_id: str) -> bool:
        previous_hash = "GENESIS"
        for row in self.audit_events(tenant_id):
            if row["previous_hash"] != previous_hash:
                return False
            event = {
                "tenant_id": row["tenant_id"],
                "action": row["action"],
                "memory_id": row["memory_id"],
                "actor_id": row["actor_id"],
                "payload": row["payload"],
                "previous_hash": row["previous_hash"],
                "created_at": row["created_at"],
            }
            if sha256_json(event) != row["audit_hash"]:
                return False
            previous_hash = row["audit_hash"]
        return True

    def count_entries(self) -> int:
        with self._connection() as connection:
            return int(connection.execute("SELECT COUNT(*) FROM memory_entries").fetchone()[0])