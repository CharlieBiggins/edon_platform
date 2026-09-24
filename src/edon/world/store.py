"""SQLite-backed institutional world state with immutable event sourcing."""

from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from copy import deepcopy
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Iterable

from edon.common.hashing import canonical_json, sha256_json


class WorldStateError(RuntimeError):
    """Raised when a world transition violates identity, version, or state rules."""


SUPPORTED_MUTATIONS = {"SET", "DELETE", "INCREMENT", "APPEND_UNIQUE", "REMOVE", "REPLACE_ROOT"}


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _identifier(value: str, label: str) -> str:
    normalized = str(value).strip()
    if not normalized or len(normalized) > 200:
        raise WorldStateError(f"{label} must contain between 1 and 200 characters")
    return normalized


def _authorization_ref(value: str) -> str:
    normalized = str(value).strip()
    if not normalized or len(normalized) > 8192:
        raise WorldStateError("authorization_ref must contain between 1 and 8192 characters")
    return normalized


def _json_object(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise WorldStateError(f"{label} must be a JSON object")
    try:
        json.dumps(value, allow_nan=False)
    except (TypeError, ValueError) as exc:
        raise WorldStateError(f"{label} must contain only finite JSON values") from exc
    return deepcopy(value)


def _path(value: Any, *, allow_root: bool = False) -> tuple[str, ...]:
    if not isinstance(value, (list, tuple)):
        raise WorldStateError("mutation path must be an array of keys")
    parts = tuple(str(part) for part in value)
    if not parts and not allow_root:
        raise WorldStateError("mutation path cannot be empty")
    if any(not part or len(part) > 200 for part in parts):
        raise WorldStateError("mutation path contains an invalid key")
    return parts


def _parent(state: dict[str, Any], path: tuple[str, ...]) -> tuple[dict[str, Any], str]:
    if not path:
        raise WorldStateError("root mutation does not have a parent")
    node: dict[str, Any] = state
    for part in path[:-1]:
        child = node.get(part)
        if not isinstance(child, dict):
            raise WorldStateError(f"mutation parent does not exist: {'.'.join(path[:-1])}")
        node = child
    return node, path[-1]


def normalize_mutations(mutations: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    for index, mutation in enumerate(mutations):
        if not isinstance(mutation, dict):
            raise WorldStateError(f"mutation {index} must be an object")
        operation = str(mutation.get("op", "")).upper()
        if operation not in SUPPORTED_MUTATIONS:
            raise WorldStateError(f"unsupported mutation operation: {operation or '<missing>'}")
        path = _path(mutation.get("path", []), allow_root=operation == "REPLACE_ROOT")
        if operation == "REPLACE_ROOT" and path:
            raise WorldStateError("REPLACE_ROOT requires an empty path")
        row: dict[str, Any] = {"op": operation, "path": list(path)}
        if operation in {"SET", "INCREMENT", "APPEND_UNIQUE", "REMOVE", "REPLACE_ROOT"}:
            if "value" not in mutation:
                raise WorldStateError(f"{operation} mutation requires value")
            try:
                json.dumps(mutation["value"], allow_nan=False)
            except (TypeError, ValueError) as exc:
                raise WorldStateError("mutation value must be finite JSON") from exc
            row["value"] = deepcopy(mutation["value"])
        normalized.append(row)
    if not normalized:
        raise WorldStateError("an event must contain at least one mutation")
    if any(row["op"] == "REPLACE_ROOT" for row in normalized) and len(normalized) != 1:
        raise WorldStateError("REPLACE_ROOT cannot be combined with other mutations")
    return normalized


def apply_mutations(initial_state: dict[str, Any], mutations: Iterable[dict[str, Any]]) -> dict[str, Any]:
    """Apply validated deterministic mutations without modifying the input object."""
    state = _json_object(initial_state, "initial_state")
    for mutation in normalize_mutations(mutations):
        operation = mutation["op"]
        path = tuple(mutation["path"])
        if operation == "REPLACE_ROOT":
            state = _json_object(mutation["value"], "replacement state")
            continue
        parent, key = _parent(state, path)
        if operation == "SET":
            parent[key] = deepcopy(mutation["value"])
        elif operation == "DELETE":
            if key not in parent:
                raise WorldStateError(f"cannot delete missing path: {'.'.join(path)}")
            del parent[key]
        elif operation == "INCREMENT":
            current = parent.get(key)
            delta = mutation["value"]
            if isinstance(current, bool) or not isinstance(current, (int, float)):
                raise WorldStateError(f"increment target is not numeric: {'.'.join(path)}")
            if isinstance(delta, bool) or not isinstance(delta, (int, float)):
                raise WorldStateError("increment value must be numeric")
            parent[key] = current + delta
        elif operation in {"APPEND_UNIQUE", "REMOVE"}:
            current = parent.get(key)
            if not isinstance(current, list):
                raise WorldStateError(f"list mutation target is not a list: {'.'.join(path)}")
            value = mutation["value"]
            if operation == "APPEND_UNIQUE" and value not in current:
                current.append(deepcopy(value))
            elif operation == "REMOVE" and value in current:
                current.remove(value)
    return state


class WorldStateStore:
    """Durable versioned state; only Kernel-authorized events should be committed."""

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
                CREATE TABLE IF NOT EXISTS worlds (
                    tenant_id TEXT NOT NULL,
                    world_id TEXT NOT NULL,
                    current_version INTEGER NOT NULL,
                    state_json TEXT NOT NULL,
                    state_sha256 TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    PRIMARY KEY (tenant_id, world_id)
                );
                CREATE TABLE IF NOT EXISTS world_events (
                    sequence INTEGER PRIMARY KEY AUTOINCREMENT,
                    tenant_id TEXT NOT NULL,
                    world_id TEXT NOT NULL,
                    event_id TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    actor_id TEXT NOT NULL,
                    expected_version INTEGER NOT NULL,
                    resulting_version INTEGER NOT NULL,
                    mutations_json TEXT NOT NULL,
                    authorization_ref TEXT NOT NULL,
                    source_lineage_json TEXT NOT NULL,
                    request_sha256 TEXT NOT NULL,
                    resulting_state_sha256 TEXT NOT NULL,
                    previous_hash TEXT NOT NULL,
                    event_hash TEXT NOT NULL UNIQUE,
                    created_at TEXT NOT NULL,
                    UNIQUE (tenant_id, world_id, event_id),
                    FOREIGN KEY (tenant_id, world_id) REFERENCES worlds(tenant_id, world_id)
                );
                CREATE TABLE IF NOT EXISTS world_snapshots (
                    tenant_id TEXT NOT NULL,
                    world_id TEXT NOT NULL,
                    version INTEGER NOT NULL,
                    state_json TEXT NOT NULL,
                    state_sha256 TEXT NOT NULL,
                    event_hash TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    PRIMARY KEY (tenant_id, world_id, version),
                    FOREIGN KEY (tenant_id, world_id) REFERENCES worlds(tenant_id, world_id)
                );
                CREATE TABLE IF NOT EXISTS world_outbox (
                    message_id TEXT PRIMARY KEY,
                    tenant_id TEXT NOT NULL,
                    world_id TEXT NOT NULL,
                    event_id TEXT NOT NULL,
                    topic TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    payload_sha256 TEXT NOT NULL,
                    status TEXT NOT NULL,
                    attempt_count INTEGER NOT NULL DEFAULT 0,
                    available_at TEXT NOT NULL,
                    lease_owner TEXT,
                    lease_expires_at TEXT,
                    last_error TEXT,
                    created_at TEXT NOT NULL,
                    delivered_at TEXT,
                    UNIQUE (topic, payload_sha256)
                );
                CREATE TABLE IF NOT EXISTS outbox_delivery_audit (
                    sequence INTEGER PRIMARY KEY AUTOINCREMENT,
                    message_id TEXT NOT NULL,
                    action TEXT NOT NULL,
                    worker_id TEXT NOT NULL,
                    detail_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (message_id) REFERENCES world_outbox(message_id)
                );
                CREATE TRIGGER IF NOT EXISTS world_events_no_update
                BEFORE UPDATE ON world_events BEGIN
                    SELECT RAISE(ABORT, 'world events are immutable');
                END;
                CREATE TRIGGER IF NOT EXISTS world_events_no_delete
                BEFORE DELETE ON world_events BEGIN
                    SELECT RAISE(ABORT, 'world events are immutable');
                END;
                CREATE TRIGGER IF NOT EXISTS world_snapshots_no_update
                BEFORE UPDATE ON world_snapshots BEGIN
                    SELECT RAISE(ABORT, 'world snapshots are immutable');
                END;
                CREATE TRIGGER IF NOT EXISTS world_snapshots_no_delete
                BEFORE DELETE ON world_snapshots BEGIN
                    SELECT RAISE(ABORT, 'world snapshots are immutable');
                END;
                CREATE TRIGGER IF NOT EXISTS outbox_delivery_audit_no_update
                BEFORE UPDATE ON outbox_delivery_audit BEGIN
                    SELECT RAISE(ABORT, 'outbox delivery audit is immutable');
                END;
                CREATE TRIGGER IF NOT EXISTS outbox_delivery_audit_no_delete
                BEFORE DELETE ON outbox_delivery_audit BEGIN
                    SELECT RAISE(ABORT, 'outbox delivery audit is immutable');
                END;
                """
            )
        self.path.chmod(0o600)

    @staticmethod
    def _snapshot(row: sqlite3.Row) -> dict[str, Any]:
        return {
            "schema_version": "edon-world-snapshot.v1",
            "tenant_id": row["tenant_id"],
            "world_id": row["world_id"],
            "version": row["version"] if "version" in row.keys() else row["current_version"],
            "state": json.loads(row["state_json"]),
            "state_sha256": row["state_sha256"],
            "event_hash": row["event_hash"] if "event_hash" in row.keys() else None,
            "created_at": row["created_at"],
            "binding_authority": False,
        }

    @staticmethod
    def _enqueue_world_event(
        connection: sqlite3.Connection,
        payload: dict[str, Any],
        event_hash: str,
        created_at: str,
    ) -> None:
        message = {
            "schema_version": "edon-world-outbox-message.v1",
            "topic": "world.events",
            "event_hash": event_hash,
            **payload,
        }
        payload_hash = sha256_json(message)
        connection.execute(
            """INSERT OR IGNORE INTO world_outbox
               (message_id, tenant_id, world_id, event_id, topic, payload_json,
                payload_sha256, status, available_at, created_at)
               VALUES (?, ?, ?, ?, 'world.events', ?, ?, 'PENDING', ?, ?)""",
            (
                "world:" + event_hash.split(":", 1)[-1],
                str(payload["tenant_id"]), str(payload["world_id"]), str(payload["event_id"]),
                canonical_json(message), payload_hash, created_at, created_at,
            ),
        )

    def create_world(
        self,
        tenant_id: str,
        world_id: str,
        initial_state: dict[str, Any],
        *,
        actor_id: str,
        authorization_ref: str,
        source_lineage: Iterable[str] = (),
        timestamp: str | None = None,
    ) -> dict[str, Any]:
        tenant_id = _identifier(tenant_id, "tenant_id")
        world_id = _identifier(world_id, "world_id")
        actor_id = _identifier(actor_id, "actor_id")
        authorization_ref = _authorization_ref(authorization_ref)
        state = _json_object(initial_state, "initial_state")
        lineages = sorted({_identifier(item, "source lineage") for item in source_lineage})
        created_at = timestamp or _now()
        state_hash = sha256_json(state)
        event_id = "WORLD_CREATED"
        request = {
            "tenant_id": tenant_id,
            "world_id": world_id,
            "event_id": event_id,
            "event_type": "WORLD_CREATED",
            "actor_id": actor_id,
            "expected_version": -1,
            "mutations": [{"op": "REPLACE_ROOT", "path": [], "value": state}],
            "authorization_ref": authorization_ref,
            "source_lineage": lineages,
        }
        request_hash = sha256_json(request)
        event = {
            **request,
            "resulting_version": 0,
            "resulting_state_sha256": state_hash,
            "previous_hash": "GENESIS",
            "created_at": created_at,
        }
        event_hash = sha256_json(event)
        with self._connection() as connection:
            connection.execute("BEGIN IMMEDIATE")
            existing = connection.execute(
                """SELECT w.*, e.request_sha256, e.event_hash
                   FROM worlds w
                   JOIN world_events e
                     ON e.tenant_id = w.tenant_id AND e.world_id = w.world_id
                   WHERE w.tenant_id = ? AND w.world_id = ?
                     AND e.event_id = 'WORLD_CREATED'""",
                (tenant_id, world_id),
            ).fetchone()
            if existing:
                if existing["request_sha256"] == request_hash:
                    snapshot = self._snapshot(existing)
                    snapshot["event_hash"] = existing["event_hash"]
                    snapshot["created_at"] = existing["updated_at"]
                    return snapshot
                raise WorldStateError("world identity is already bound to different initial state")
            connection.execute(
                """INSERT INTO worlds
                   (tenant_id, world_id, current_version, state_json, state_sha256, created_at, updated_at)
                   VALUES (?, ?, 0, ?, ?, ?, ?)""",
                (tenant_id, world_id, canonical_json(state), state_hash, created_at, created_at),
            )
            connection.execute(
                """INSERT INTO world_events
                   (tenant_id, world_id, event_id, event_type, actor_id, expected_version,
                    resulting_version, mutations_json, authorization_ref, source_lineage_json,
                    request_sha256, resulting_state_sha256, previous_hash, event_hash, created_at)
                   VALUES (?, ?, ?, ?, ?, -1, 0, ?, ?, ?, ?, ?, 'GENESIS', ?, ?)""",
                (
                    tenant_id, world_id, event_id, "WORLD_CREATED", actor_id,
                    canonical_json(request["mutations"]), authorization_ref,
                    canonical_json(lineages), request_hash, state_hash, event_hash, created_at,
                ),
            )
            connection.execute(
                """INSERT INTO world_snapshots
                   (tenant_id, world_id, version, state_json, state_sha256, event_hash, created_at)
                   VALUES (?, ?, 0, ?, ?, ?, ?)""",
                (tenant_id, world_id, canonical_json(state), state_hash, event_hash, created_at),
            )
            self._enqueue_world_event(
                connection,
                {
                    "tenant_id": tenant_id,
                    "world_id": world_id,
                    "event_id": event_id,
                    "event_type": "WORLD_CREATED",
                    "actor_id": actor_id,
                    "expected_version": -1,
                    "resulting_version": 0,
                    "mutations": request["mutations"],
                    "authorization_ref_sha256": sha256_json(authorization_ref),
                    "source_lineage": lineages,
                    "resulting_state_sha256": state_hash,
                },
                event_hash,
                created_at,
            )
        return self.state_at(tenant_id, world_id, 0)

    def append_event(
        self,
        tenant_id: str,
        world_id: str,
        event_id: str,
        event_type: str,
        mutations: Iterable[dict[str, Any]],
        *,
        actor_id: str,
        expected_version: int,
        authorization_ref: str,
        source_lineage: Iterable[str] = (),
        timestamp: str | None = None,
    ) -> dict[str, Any]:
        tenant_id = _identifier(tenant_id, "tenant_id")
        world_id = _identifier(world_id, "world_id")
        event_id = _identifier(event_id, "event_id")
        event_type = _identifier(event_type, "event_type")
        actor_id = _identifier(actor_id, "actor_id")
        authorization_ref = _authorization_ref(authorization_ref)
        normalized = normalize_mutations(mutations)
        lineages = sorted({_identifier(item, "source lineage") for item in source_lineage})
        request = {
            "tenant_id": tenant_id,
            "world_id": world_id,
            "event_id": event_id,
            "event_type": event_type,
            "actor_id": actor_id,
            "expected_version": int(expected_version),
            "mutations": normalized,
            "authorization_ref": authorization_ref,
            "source_lineage": lineages,
        }
        request_hash = sha256_json(request)
        created_at = timestamp or _now()
        with self._connection() as connection:
            connection.execute("BEGIN IMMEDIATE")
            duplicate = connection.execute(
                """SELECT request_sha256, resulting_version FROM world_events
                   WHERE tenant_id = ? AND world_id = ? AND event_id = ?""",
                (tenant_id, world_id, event_id),
            ).fetchone()
            if duplicate:
                if duplicate["request_sha256"] != request_hash:
                    raise WorldStateError("event identity is already bound to different content")
                snapshot = connection.execute(
                    """SELECT * FROM world_snapshots
                       WHERE tenant_id = ? AND world_id = ? AND version = ?""",
                    (tenant_id, world_id, int(duplicate["resulting_version"])),
                ).fetchone()
                if not snapshot:
                    raise WorldStateError("idempotent event snapshot is missing")
                return self._snapshot(snapshot)
            world = connection.execute(
                "SELECT * FROM worlds WHERE tenant_id = ? AND world_id = ?",
                (tenant_id, world_id),
            ).fetchone()
            if not world:
                raise WorldStateError("world not found for tenant")
            if int(world["current_version"]) != int(expected_version):
                raise WorldStateError(
                    f"world version conflict: expected {expected_version}, current {world['current_version']}"
                )
            prior_state = json.loads(world["state_json"])
            resulting_state = apply_mutations(prior_state, normalized)
            resulting_hash = sha256_json(resulting_state)
            resulting_version = int(world["current_version"]) + 1
            previous = connection.execute(
                """SELECT event_hash FROM world_events
                   WHERE tenant_id = ? AND world_id = ? ORDER BY sequence DESC LIMIT 1""",
                (tenant_id, world_id),
            ).fetchone()
            previous_hash = previous["event_hash"] if previous else "GENESIS"
            event = {
                **request,
                "resulting_version": resulting_version,
                "resulting_state_sha256": resulting_hash,
                "previous_hash": previous_hash,
                "created_at": created_at,
            }
            event_hash = sha256_json(event)
            connection.execute(
                """INSERT INTO world_events
                   (tenant_id, world_id, event_id, event_type, actor_id, expected_version,
                    resulting_version, mutations_json, authorization_ref, source_lineage_json,
                    request_sha256, resulting_state_sha256, previous_hash, event_hash, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    tenant_id, world_id, event_id, event_type, actor_id, int(expected_version),
                    resulting_version, canonical_json(normalized), authorization_ref,
                    canonical_json(lineages), request_hash, resulting_hash, previous_hash,
                    event_hash, created_at,
                ),
            )
            connection.execute(
                """INSERT INTO world_snapshots
                   (tenant_id, world_id, version, state_json, state_sha256, event_hash, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (
                    tenant_id, world_id, resulting_version, canonical_json(resulting_state),
                    resulting_hash, event_hash, created_at,
                ),
            )
            connection.execute(
                """UPDATE worlds SET current_version = ?, state_json = ?, state_sha256 = ?, updated_at = ?
                   WHERE tenant_id = ? AND world_id = ?""",
                (
                    resulting_version, canonical_json(resulting_state), resulting_hash,
                    created_at, tenant_id, world_id,
                ),
            )
            self._enqueue_world_event(
                connection,
                {
                    "tenant_id": tenant_id,
                    "world_id": world_id,
                    "event_id": event_id,
                    "event_type": event_type,
                    "actor_id": actor_id,
                    "expected_version": int(expected_version),
                    "resulting_version": resulting_version,
                    "mutations": normalized,
                    "authorization_ref_sha256": sha256_json(authorization_ref),
                    "source_lineage": lineages,
                    "resulting_state_sha256": resulting_hash,
                },
                event_hash,
                created_at,
            )
        return self.state_at(tenant_id, world_id, resulting_version)

    def restore_version(
        self,
        tenant_id: str,
        world_id: str,
        target_version: int,
        *,
        event_id: str,
        actor_id: str,
        expected_version: int,
        authorization_ref: str,
        timestamp: str | None = None,
    ) -> dict[str, Any]:
        target = self.state_at(tenant_id, world_id, int(target_version))
        return self.append_event(
            tenant_id,
            world_id,
            event_id,
            "WORLD_RESTORED",
            [{"op": "REPLACE_ROOT", "path": [], "value": target["state"]}],
            actor_id=actor_id,
            expected_version=expected_version,
            authorization_ref=authorization_ref,
            source_lineage=[f"snapshot:{world_id}@{target_version}:{target['state_sha256']}"],
            timestamp=timestamp,
        )

    def get_world(self, tenant_id: str, world_id: str) -> dict[str, Any]:
        tenant_id = _identifier(tenant_id, "tenant_id")
        world_id = _identifier(world_id, "world_id")
        with self._connection() as connection:
            row = connection.execute(
                "SELECT * FROM worlds WHERE tenant_id = ? AND world_id = ?",
                (tenant_id, world_id),
            ).fetchone()
            if not row:
                raise WorldStateError("world not found for tenant")
            snapshot = self._snapshot(row)
            latest = connection.execute(
                """SELECT event_hash FROM world_events WHERE tenant_id = ? AND world_id = ?
                   ORDER BY sequence DESC LIMIT 1""",
                (tenant_id, world_id),
            ).fetchone()
            snapshot["event_hash"] = latest["event_hash"] if latest else None
            snapshot["created_at"] = row["updated_at"]
            return snapshot

    def state_at(self, tenant_id: str, world_id: str, version: int) -> dict[str, Any]:
        tenant_id = _identifier(tenant_id, "tenant_id")
        world_id = _identifier(world_id, "world_id")
        with self._connection() as connection:
            row = connection.execute(
                """SELECT * FROM world_snapshots
                   WHERE tenant_id = ? AND world_id = ? AND version = ?""",
                (tenant_id, world_id, int(version)),
            ).fetchone()
            if not row:
                raise WorldStateError("world snapshot not found for tenant and version")
            return self._snapshot(row)

    def list_worlds(self, tenant_id: str) -> list[dict[str, Any]]:
        tenant_id = _identifier(tenant_id, "tenant_id")
        with self._connection() as connection:
            return [
                {
                    "tenant_id": row["tenant_id"],
                    "world_id": row["world_id"],
                    "version": row["current_version"],
                    "state_sha256": row["state_sha256"],
                    "updated_at": row["updated_at"],
                }
                for row in connection.execute(
                    "SELECT * FROM worlds WHERE tenant_id = ? ORDER BY world_id", (tenant_id,)
                )
            ]

    def events(self, tenant_id: str, world_id: str) -> list[dict[str, Any]]:
        tenant_id = _identifier(tenant_id, "tenant_id")
        world_id = _identifier(world_id, "world_id")
        with self._connection() as connection:
            return [
                {
                    "sequence": row["sequence"],
                    "tenant_id": row["tenant_id"],
                    "world_id": row["world_id"],
                    "event_id": row["event_id"],
                    "event_type": row["event_type"],
                    "actor_id": row["actor_id"],
                    "expected_version": row["expected_version"],
                    "resulting_version": row["resulting_version"],
                    "mutations": json.loads(row["mutations_json"]),
                    "authorization_ref": row["authorization_ref"],
                    "source_lineage": json.loads(row["source_lineage_json"]),
                    "request_sha256": row["request_sha256"],
                    "resulting_state_sha256": row["resulting_state_sha256"],
                    "previous_hash": row["previous_hash"],
                    "event_hash": row["event_hash"],
                    "created_at": row["created_at"],
                }
                for row in connection.execute(
                    """SELECT * FROM world_events WHERE tenant_id = ? AND world_id = ?
                       ORDER BY sequence""",
                    (tenant_id, world_id),
                )
            ]

    def verify_world(self, tenant_id: str, world_id: str) -> dict[str, Any]:
        records = self.events(tenant_id, world_id)
        checks = {
            "creation_event_present": bool(records) and records[0]["event_type"] == "WORLD_CREATED",
            "event_hash_chain_valid": True,
            "versions_contiguous": True,
            "snapshots_match_replay": True,
            "current_state_matches_replay": True,
        }
        previous_hash = "GENESIS"
        state: dict[str, Any] | None = None
        previous_version = -1
        for record in records:
            request = {
                "tenant_id": record["tenant_id"],
                "world_id": record["world_id"],
                "event_id": record["event_id"],
                "event_type": record["event_type"],
                "actor_id": record["actor_id"],
                "expected_version": record["expected_version"],
                "mutations": record["mutations"],
                "authorization_ref": record["authorization_ref"],
                "source_lineage": record["source_lineage"],
            }
            event = {
                **request,
                "resulting_version": record["resulting_version"],
                "resulting_state_sha256": record["resulting_state_sha256"],
                "previous_hash": record["previous_hash"],
                "created_at": record["created_at"],
            }
            if record["request_sha256"] != sha256_json(request):
                checks["event_hash_chain_valid"] = False
            if record["previous_hash"] != previous_hash or record["event_hash"] != sha256_json(event):
                checks["event_hash_chain_valid"] = False
            if record["expected_version"] != previous_version or record["resulting_version"] != previous_version + 1:
                checks["versions_contiguous"] = False
            state = apply_mutations(state or {}, record["mutations"])
            if sha256_json(state) != record["resulting_state_sha256"]:
                checks["snapshots_match_replay"] = False
            try:
                snapshot = self.state_at(tenant_id, world_id, record["resulting_version"])
            except WorldStateError:
                checks["snapshots_match_replay"] = False
            else:
                if snapshot["state"] != state or snapshot["state_sha256"] != sha256_json(state):
                    checks["snapshots_match_replay"] = False
            previous_hash = record["event_hash"]
            previous_version = record["resulting_version"]
        try:
            current = self.get_world(tenant_id, world_id)
        except WorldStateError:
            checks["current_state_matches_replay"] = False
        else:
            if state is None or current["state"] != state or current["state_sha256"] != sha256_json(state):
                checks["current_state_matches_replay"] = False
        return {
            "tenant_id": tenant_id,
            "world_id": world_id,
            "event_count": len(records),
            "checks": checks,
            "passed": all(checks.values()),
            "binding_authority": False,
        }

    def count_worlds(self) -> int:
        with self._connection() as connection:
            return int(connection.execute("SELECT COUNT(*) FROM worlds").fetchone()[0])