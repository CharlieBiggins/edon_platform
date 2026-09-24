"""Lease-based delivery over the outbox stored transactionally with world events."""

from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from edon.common.hashing import canonical_json


class OutboxError(RuntimeError):
    """Raised when a delivery lease or state transition is invalid."""


def _now() -> datetime:
    return datetime.now(UTC)


def _time(value: datetime | str | None) -> datetime:
    if value is None:
        return _now()
    if isinstance(value, datetime):
        parsed = value
    else:
        try:
            parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        except ValueError as exc:
            raise OutboxError("timestamp must be ISO-8601") from exc
    if parsed.tzinfo is None:
        raise OutboxError("timestamp must include a timezone")
    return parsed.astimezone(UTC)


class TransactionalOutbox:
    """Claims, acknowledges, retries, and audits world-outbox messages."""

    def __init__(self, world_database: Path | str):
        self.path = Path(world_database)
        if not self.path.is_file():
            raise OutboxError("world database must be initialized before opening the outbox")

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

    @staticmethod
    def _message(row: sqlite3.Row) -> dict[str, Any]:
        return {
            "message_id": row["message_id"],
            "tenant_id": row["tenant_id"],
            "world_id": row["world_id"],
            "event_id": row["event_id"],
            "topic": row["topic"],
            "payload": json.loads(row["payload_json"]),
            "payload_sha256": row["payload_sha256"],
            "status": row["status"],
            "attempt_count": row["attempt_count"],
            "available_at": row["available_at"],
            "lease_owner": row["lease_owner"],
            "lease_expires_at": row["lease_expires_at"],
            "last_error": row["last_error"],
            "created_at": row["created_at"],
            "delivered_at": row["delivered_at"],
        }

    @staticmethod
    def _audit(
        connection: sqlite3.Connection,
        message_id: str,
        action: str,
        worker_id: str,
        detail: dict[str, Any],
        created_at: str,
    ) -> None:
        connection.execute(
            """INSERT INTO outbox_delivery_audit
               (message_id, action, worker_id, detail_json, created_at)
               VALUES (?, ?, ?, ?, ?)""",
            (message_id, action, worker_id, canonical_json(detail), created_at),
        )

    def claim(
        self,
        worker_id: str,
        *,
        limit: int = 100,
        lease_seconds: int = 30,
        now: datetime | str | None = None,
    ) -> list[dict[str, Any]]:
        worker_id = str(worker_id).strip()
        if not worker_id or len(worker_id) > 200:
            raise OutboxError("worker_id must contain between 1 and 200 characters")
        limit = int(limit)
        lease_seconds = int(lease_seconds)
        if limit < 1 or limit > 1000:
            raise OutboxError("claim limit must be between 1 and 1000")
        if lease_seconds < 1 or lease_seconds > 3600:
            raise OutboxError("lease_seconds must be between 1 and 3600")
        current = _time(now)
        current_text = current.isoformat()
        lease_expiry = (current + timedelta(seconds=lease_seconds)).isoformat()
        claimed: list[dict[str, Any]] = []
        with self._connection() as connection:
            connection.execute("BEGIN IMMEDIATE")
            expired = list(connection.execute(
                """SELECT message_id, lease_owner FROM world_outbox
                   WHERE status = 'LEASED' AND lease_expires_at < ?""",
                (current_text,),
            ))
            for row in expired:
                connection.execute(
                    """UPDATE world_outbox
                       SET status = 'PENDING', lease_owner = NULL, lease_expires_at = NULL
                       WHERE message_id = ?""",
                    (row["message_id"],),
                )
                self._audit(
                    connection, row["message_id"], "LEASE_EXPIRED",
                    str(row["lease_owner"] or "UNKNOWN"), {}, current_text,
                )
            rows = list(connection.execute(
                """SELECT * FROM world_outbox
                   WHERE status = 'PENDING' AND available_at <= ?
                   ORDER BY created_at, message_id LIMIT ?""",
                (current_text, limit),
            ))
            for row in rows:
                connection.execute(
                    """UPDATE world_outbox
                       SET status = 'LEASED', lease_owner = ?, lease_expires_at = ?,
                           attempt_count = attempt_count + 1
                       WHERE message_id = ? AND status = 'PENDING'""",
                    (worker_id, lease_expiry, row["message_id"]),
                )
                self._audit(
                    connection, row["message_id"], "CLAIMED", worker_id,
                    {"lease_expires_at": lease_expiry}, current_text,
                )
                updated = connection.execute(
                    "SELECT * FROM world_outbox WHERE message_id = ?", (row["message_id"],)
                ).fetchone()
                if updated:
                    claimed.append(self._message(updated))
        return claimed

    def acknowledge(
        self,
        message_id: str,
        worker_id: str,
        *,
        now: datetime | str | None = None,
    ) -> dict[str, Any]:
        current = _time(now).isoformat()
        with self._connection() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT * FROM world_outbox WHERE message_id = ?", (message_id,)
            ).fetchone()
            if not row:
                raise OutboxError("outbox message not found")
            if row["status"] == "DELIVERED":
                return self._message(row)
            if row["status"] != "LEASED" or row["lease_owner"] != worker_id:
                raise OutboxError("outbox message is not leased by this worker")
            connection.execute(
                """UPDATE world_outbox
                   SET status = 'DELIVERED', delivered_at = ?, lease_owner = NULL,
                       lease_expires_at = NULL, last_error = NULL
                   WHERE message_id = ?""",
                (current, message_id),
            )
            self._audit(connection, message_id, "DELIVERED", worker_id, {}, current)
            delivered = connection.execute(
                "SELECT * FROM world_outbox WHERE message_id = ?", (message_id,)
            ).fetchone()
        assert delivered is not None
        return self._message(delivered)

    def fail(
        self,
        message_id: str,
        worker_id: str,
        error: str,
        *,
        retry_after_seconds: int = 5,
        max_attempts: int = 5,
        now: datetime | str | None = None,
    ) -> dict[str, Any]:
        current = _time(now)
        error = str(error).strip()[:2000]
        if not error:
            raise OutboxError("delivery error must be explicit")
        with self._connection() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT * FROM world_outbox WHERE message_id = ?", (message_id,)
            ).fetchone()
            if not row or row["status"] != "LEASED" or row["lease_owner"] != worker_id:
                raise OutboxError("outbox message is not leased by this worker")
            dead = int(row["attempt_count"]) >= int(max_attempts)
            status = "DEAD" if dead else "PENDING"
            available = (current + timedelta(seconds=int(retry_after_seconds))).isoformat()
            connection.execute(
                """UPDATE world_outbox
                   SET status = ?, available_at = ?, lease_owner = NULL,
                       lease_expires_at = NULL, last_error = ?
                   WHERE message_id = ?""",
                (status, available, error, message_id),
            )
            self._audit(
                connection, message_id, "DEAD" if dead else "RETRY_SCHEDULED",
                worker_id, {"error": error, "available_at": available}, current.isoformat(),
            )
            updated = connection.execute(
                "SELECT * FROM world_outbox WHERE message_id = ?", (message_id,)
            ).fetchone()
        assert updated is not None
        return self._message(updated)

    def list_messages(self, *, status: str | None = None) -> list[dict[str, Any]]:
        with self._connection() as connection:
            if status is None:
                rows = connection.execute("SELECT * FROM world_outbox ORDER BY created_at, message_id")
            else:
                rows = connection.execute(
                    "SELECT * FROM world_outbox WHERE status = ? ORDER BY created_at, message_id",
                    (str(status).upper(),),
                )
            return [self._message(row) for row in rows]

    def audit_events(self) -> list[dict[str, Any]]:
        with self._connection() as connection:
            return [
                {
                    "sequence": row["sequence"],
                    "message_id": row["message_id"],
                    "action": row["action"],
                    "worker_id": row["worker_id"],
                    "detail": json.loads(row["detail_json"]),
                    "created_at": row["created_at"],
                }
                for row in connection.execute(
                    "SELECT * FROM outbox_delivery_audit ORDER BY sequence"
                )
            ]