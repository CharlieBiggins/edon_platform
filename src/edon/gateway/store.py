"""SQLite custody for disabled-by-default Agent Gateway connectors and messages."""

from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from edon.common.hashing import canonical_json, sha256_json

from .models import AgentGatewayError


def _now() -> str:
    return datetime.now(UTC).isoformat()


class AgentGatewayStore:
    """Tenant-scoped connector registry and immutable gateway-message custody."""

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
                CREATE TABLE IF NOT EXISTS gateway_connectors (
                    tenant_id TEXT NOT NULL,
                    connector_id TEXT NOT NULL,
                    profile_json TEXT NOT NULL,
                    profile_sha256 TEXT NOT NULL,
                    status TEXT NOT NULL,
                    security_review_ref TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    PRIMARY KEY (tenant_id, connector_id)
                );
                CREATE TABLE IF NOT EXISTS gateway_messages (
                    sequence INTEGER PRIMARY KEY AUTOINCREMENT,
                    tenant_id TEXT NOT NULL,
                    connector_id TEXT NOT NULL,
                    direction TEXT NOT NULL,
                    message_id TEXT NOT NULL,
                    idempotency_key TEXT NOT NULL,
                    envelope_json TEXT NOT NULL,
                    envelope_sha256 TEXT NOT NULL,
                    receipt_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    UNIQUE (tenant_id, connector_id, direction, message_id),
                    UNIQUE (tenant_id, connector_id, direction, idempotency_key),
                    FOREIGN KEY (tenant_id, connector_id)
                        REFERENCES gateway_connectors(tenant_id, connector_id)
                );
                CREATE TABLE IF NOT EXISTS gateway_audit (
                    sequence INTEGER PRIMARY KEY AUTOINCREMENT,
                    tenant_id TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    entity_id TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    previous_hash TEXT NOT NULL,
                    event_hash TEXT NOT NULL UNIQUE,
                    created_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS gateway_message_lookup
                    ON gateway_messages(tenant_id, connector_id, direction, sequence);
                CREATE INDEX IF NOT EXISTS gateway_audit_tenant_lookup
                    ON gateway_audit(tenant_id, sequence);
                CREATE TRIGGER IF NOT EXISTS gateway_messages_no_update
                BEFORE UPDATE ON gateway_messages BEGIN
                    SELECT RAISE(ABORT, 'gateway messages are immutable');
                END;
                CREATE TRIGGER IF NOT EXISTS gateway_messages_no_delete
                BEFORE DELETE ON gateway_messages BEGIN
                    SELECT RAISE(ABORT, 'gateway messages are immutable');
                END;
                CREATE TRIGGER IF NOT EXISTS gateway_audit_no_update
                BEFORE UPDATE ON gateway_audit BEGIN
                    SELECT RAISE(ABORT, 'gateway audit is immutable');
                END;
                CREATE TRIGGER IF NOT EXISTS gateway_audit_no_delete
                BEFORE DELETE ON gateway_audit BEGIN
                    SELECT RAISE(ABORT, 'gateway audit is immutable');
                END;
                """
            )
        self.path.chmod(0o600)

    @staticmethod
    def _decode_connector(row: sqlite3.Row) -> dict[str, Any]:
        record = json.loads(row["profile_json"])
        record.update(
            {
                "status": row["status"],
                "enabled": row["status"] == "ENABLED",
                "security_review_ref": row["security_review_ref"],
                "profile_sha256": row["profile_sha256"],
                "created_at": row["created_at"],
                "updated_at": row["updated_at"],
                "binding_authority": False,
            }
        )
        return record

    @staticmethod
    def _decode_message(row: sqlite3.Row) -> dict[str, Any]:
        return {
            "sequence": row["sequence"],
            "envelope": json.loads(row["envelope_json"]),
            "receipt": json.loads(row["receipt_json"]),
            "created_at": row["created_at"],
            "binding_authority": False,
        }

    def _append_audit(
        self,
        connection: sqlite3.Connection,
        tenant_id: str,
        event_type: str,
        entity_id: str,
        payload: dict[str, Any],
        created_at: str,
    ) -> str:
        previous = connection.execute(
            "SELECT event_hash FROM gateway_audit ORDER BY sequence DESC LIMIT 1"
        ).fetchone()
        previous_hash = previous["event_hash"] if previous else "GENESIS"
        audit_payload = {"tenant_id": tenant_id, **payload}
        event = {
            "tenant_id": tenant_id,
            "event_type": event_type,
            "entity_id": entity_id,
            "payload": audit_payload,
            "previous_hash": previous_hash,
            "created_at": created_at,
        }
        event_hash = sha256_json(event)
        connection.execute(
            """INSERT INTO gateway_audit
               (tenant_id, event_type, entity_id, payload_json, previous_hash,
                event_hash, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                tenant_id,
                event_type,
                entity_id,
                canonical_json(audit_payload),
                previous_hash,
                event_hash,
                created_at,
            ),
        )
        return event_hash

    def register_connector(
        self,
        profile: dict[str, Any],
        *,
        actor_id: str,
        timestamp: str | None = None,
    ) -> dict[str, Any]:
        created_at = timestamp or _now()
        profile_sha256 = sha256_json(profile)
        tenant_id = str(profile["tenant_id"])
        connector_id = str(profile["connector_id"])
        with self._connection() as connection:
            existing = connection.execute(
                """SELECT * FROM gateway_connectors
                   WHERE tenant_id = ? AND connector_id = ?""",
                (tenant_id, connector_id),
            ).fetchone()
            if existing:
                if existing["profile_sha256"] != profile_sha256:
                    raise AgentGatewayError(
                        "connector identity is already bound to different configuration"
                    )
                return self._decode_connector(existing)
            connection.execute(
                """INSERT INTO gateway_connectors
                   (tenant_id, connector_id, profile_json, profile_sha256, status,
                    security_review_ref, created_at, updated_at)
                   VALUES (?, ?, ?, ?, 'DISABLED', NULL, ?, ?)""",
                (
                    tenant_id,
                    connector_id,
                    canonical_json(profile),
                    profile_sha256,
                    created_at,
                    created_at,
                ),
            )
            self._append_audit(
                connection,
                tenant_id,
                "CONNECTOR_REGISTERED",
                connector_id,
                {
                    "actor_id": actor_id,
                    "profile_sha256": profile_sha256,
                    "status": "DISABLED",
                },
                created_at,
            )
            row = connection.execute(
                """SELECT * FROM gateway_connectors
                   WHERE tenant_id = ? AND connector_id = ?""",
                (tenant_id, connector_id),
            ).fetchone()
        assert row is not None
        return self._decode_connector(row)

    def connector(self, tenant_id: str, connector_id: str) -> dict[str, Any]:
        with self._connection() as connection:
            row = connection.execute(
                """SELECT * FROM gateway_connectors
                   WHERE tenant_id = ? AND connector_id = ?""",
                (tenant_id, connector_id),
            ).fetchone()
        if not row:
            raise AgentGatewayError("unknown connector for tenant")
        return self._decode_connector(row)

    def set_connector_status(
        self,
        tenant_id: str,
        connector_id: str,
        status: str,
        *,
        security_review_ref: str | None,
        actor_id: str,
        timestamp: str | None = None,
    ) -> dict[str, Any]:
        updated_at = timestamp or _now()
        with self._connection() as connection:
            row = connection.execute(
                """SELECT * FROM gateway_connectors
                   WHERE tenant_id = ? AND connector_id = ?""",
                (tenant_id, connector_id),
            ).fetchone()
            if not row:
                raise AgentGatewayError("unknown connector for tenant")
            review = security_review_ref or row["security_review_ref"]
            connection.execute(
                """UPDATE gateway_connectors
                   SET status = ?, security_review_ref = ?, updated_at = ?
                   WHERE tenant_id = ? AND connector_id = ?""",
                (status, review, updated_at, tenant_id, connector_id),
            )
            self._append_audit(
                connection,
                tenant_id,
                "CONNECTOR_STATUS_CHANGED",
                connector_id,
                {
                    "actor_id": actor_id,
                    "previous_status": row["status"],
                    "status": status,
                    "security_review_ref": review,
                },
                updated_at,
            )
            updated = connection.execute(
                """SELECT * FROM gateway_connectors
                   WHERE tenant_id = ? AND connector_id = ?""",
                (tenant_id, connector_id),
            ).fetchone()
        assert updated is not None
        return self._decode_connector(updated)

    def record_envelope(
        self,
        envelope: dict[str, Any],
        *,
        receipt_status: str,
        actor_id: str,
        timestamp: str | None = None,
    ) -> dict[str, Any]:
        created_at = timestamp or _now()
        tenant_id = str(envelope["tenant_id"])
        connector_id = str(envelope["connector_id"])
        direction = str(envelope["direction"])
        envelope_sha256 = str(envelope["envelope_sha256"])
        with self._connection() as connection:
            existing = connection.execute(
                """SELECT * FROM gateway_messages
                   WHERE tenant_id = ? AND connector_id = ? AND direction = ?
                     AND idempotency_key = ?""",
                (
                    tenant_id,
                    connector_id,
                    direction,
                    str(envelope["idempotency_key"]),
                ),
            ).fetchone()
            if existing:
                if existing["envelope_sha256"] != envelope_sha256:
                    raise AgentGatewayError(
                        "idempotency key is already bound to different message content"
                    )
                return json.loads(existing["receipt_json"])
            message_existing = connection.execute(
                """SELECT * FROM gateway_messages
                   WHERE tenant_id = ? AND connector_id = ? AND direction = ?
                     AND message_id = ?""",
                (tenant_id, connector_id, direction, str(envelope["message_id"])),
            ).fetchone()
            if message_existing:
                if message_existing["envelope_sha256"] != envelope_sha256:
                    raise AgentGatewayError(
                        "message identity is already bound to different content"
                    )
                return json.loads(message_existing["receipt_json"])
            receipt = {
                "schema_version": "edon-agent-gateway-receipt.v1",
                "status": receipt_status,
                "message_id": envelope["message_id"],
                "tenant_id": tenant_id,
                "connector_id": connector_id,
                "direction": direction,
                "envelope_sha256": envelope_sha256,
                "delivered": False,
                "executed": False,
                "binding_authority": False,
            }
            connection.execute(
                """INSERT INTO gateway_messages
                   (tenant_id, connector_id, direction, message_id, idempotency_key,
                    envelope_json, envelope_sha256, receipt_json, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    tenant_id,
                    connector_id,
                    direction,
                    str(envelope["message_id"]),
                    str(envelope["idempotency_key"]),
                    canonical_json(envelope),
                    envelope_sha256,
                    canonical_json(receipt),
                    created_at,
                ),
            )
            self._append_audit(
                connection,
                tenant_id,
                "GATEWAY_MESSAGE_RECORDED",
                str(envelope["message_id"]),
                {
                    "actor_id": actor_id,
                    "connector_id": connector_id,
                    "direction": direction,
                    "envelope_sha256": envelope_sha256,
                    "receipt_status": receipt_status,
                },
                created_at,
            )
        return receipt

    def list_connectors(self, tenant_id: str) -> list[dict[str, Any]]:
        with self._connection() as connection:
            rows = connection.execute(
                """SELECT * FROM gateway_connectors
                   WHERE tenant_id = ? ORDER BY connector_id""",
                (tenant_id,),
            ).fetchall()
        return [self._decode_connector(row) for row in rows]

    def list_messages(
        self,
        tenant_id: str,
        *,
        connector_id: str | None = None,
        direction: str | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        if limit < 1 or limit > 1000:
            raise AgentGatewayError("message query limit must be between 1 and 1000")
        clauses = ["tenant_id = ?"]
        values: list[Any] = [tenant_id]
        if connector_id:
            clauses.append("connector_id = ?")
            values.append(connector_id)
        if direction:
            normalized = direction.upper()
            if normalized not in {"INGRESS", "EGRESS"}:
                raise AgentGatewayError("message direction must be INGRESS or EGRESS")
            clauses.append("direction = ?")
            values.append(normalized)
        values.append(limit)
        query = (
            "SELECT * FROM gateway_messages WHERE "
            + " AND ".join(clauses)
            + " ORDER BY sequence DESC LIMIT ?"
        )
        with self._connection() as connection:
            rows = connection.execute(query, values).fetchall()
        return [self._decode_message(row) for row in rows]

    def audit_events(self, tenant_id: str | None = None) -> list[dict[str, Any]]:
        query = "SELECT * FROM gateway_audit"
        values: tuple[Any, ...] = ()
        if tenant_id:
            query += " WHERE tenant_id = ?"
            values = (tenant_id,)
        query += " ORDER BY sequence"
        with self._connection() as connection:
            rows = connection.execute(query, values).fetchall()
        return [
            {
                "sequence": row["sequence"],
                "tenant_id": row["tenant_id"],
                "event_type": row["event_type"],
                "entity_id": row["entity_id"],
                "payload": json.loads(row["payload_json"]),
                "previous_hash": row["previous_hash"],
                "event_hash": row["event_hash"],
                "created_at": row["created_at"],
                "binding_authority": False,
            }
            for row in rows
        ]

    def verify_audit_chain(self) -> bool:
        previous_hash = "GENESIS"
        for event in self.audit_events():
            if event["previous_hash"] != previous_hash:
                return False
            core = {
                "tenant_id": event["tenant_id"],
                "event_type": event["event_type"],
                "entity_id": event["entity_id"],
                "payload": event["payload"],
                "previous_hash": event["previous_hash"],
                "created_at": event["created_at"],
            }
            if sha256_json(core) != event["event_hash"]:
                return False
            previous_hash = event["event_hash"]
        return True

    def counts(self) -> dict[str, int]:
        with self._connection() as connection:
            connectors = connection.execute(
                "SELECT COUNT(*) AS count FROM gateway_connectors"
            ).fetchone()["count"]
            messages = connection.execute(
                "SELECT COUNT(*) AS count FROM gateway_messages"
            ).fetchone()["count"]
            audit = connection.execute(
                "SELECT COUNT(*) AS count FROM gateway_audit"
            ).fetchone()["count"]
        return {
            "connectors": int(connectors),
            "messages": int(messages),
            "audit_events": int(audit),
        }