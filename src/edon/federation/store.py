"""Immutable hierarchy, redacted projections, and cross-scope escalation custody."""

from __future__ import annotations

import json
import math
import sqlite3
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Iterable

from edon.common.hashing import sha256_json
from edon.world import WorldStateStore


class FederationError(RuntimeError):
    """Raised when a federation record violates hierarchy or disclosure rules."""


SCOPE_RANK = {"GLOBAL": 0, "DOMAIN": 1, "REGION": 2, "FACILITY": 3, "EDGE": 4}
LATENCY_CLASSES = {"MILLISECONDS", "SECONDS", "MINUTES", "HOURS", "DAYS"}
SEVERITIES = {"INFO", "LOW", "MEDIUM", "HIGH", "CRITICAL"}


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _identifier(value: Any, label: str) -> str:
    normalized = str(value).strip()
    if not normalized or len(normalized) > 200:
        raise FederationError(f"{label} must contain between 1 and 200 characters")
    return normalized


def _score(value: Any, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise FederationError(f"{label} must be numeric")
    result = float(value)
    if not math.isfinite(result) or not 0 <= result <= 1:
        raise FederationError(f"{label} must be between 0 and 1")
    return result


def _json(value: Any, label: str) -> str:
    if not isinstance(value, dict):
        raise FederationError(f"{label} must be a JSON object")
    try:
        return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)
    except (TypeError, ValueError) as exc:
        raise FederationError(f"{label} must contain finite JSON values") from exc


def _counts(records: dict[str, dict[str, Any]], field: str) -> dict[str, int]:
    result: dict[str, int] = {}
    for record in records.values():
        key = str(record.get(field, "UNKNOWN"))
        result[key] = result.get(key, 0) + 1
    return dict(sorted(result.items()))


class InstitutionalFederationStore:
    """Stores an immutable scope tree and non-binding coordination records."""

    def __init__(self, path: Path | str, worlds: WorldStateStore):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.worlds = worlds
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA journal_mode = WAL")
        connection.execute("PRAGMA foreign_keys = ON")
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
                CREATE TABLE IF NOT EXISTS federation_scopes (
                    tenant_id TEXT NOT NULL,
                    scope_id TEXT NOT NULL,
                    parent_scope_id TEXT,
                    scope_type TEXT NOT NULL,
                    world_id TEXT,
                    name TEXT NOT NULL,
                    authority_domain TEXT NOT NULL,
                    decision_latency_class TEXT NOT NULL,
                    data_policy_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    record_sha256 TEXT NOT NULL,
                    PRIMARY KEY (tenant_id, scope_id),
                    UNIQUE (tenant_id, world_id)
                );
                CREATE TABLE IF NOT EXISTS federation_projections (
                    tenant_id TEXT NOT NULL,
                    projection_id TEXT NOT NULL,
                    projection_kind TEXT NOT NULL,
                    source_scope_id TEXT NOT NULL,
                    target_scope_id TEXT NOT NULL,
                    source_world_id TEXT,
                    source_world_version INTEGER,
                    source_state_sha256 TEXT,
                    summary_json TEXT NOT NULL,
                    summary_sha256 TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    PRIMARY KEY (tenant_id, projection_id)
                );
                CREATE TABLE IF NOT EXISTS federation_routes (
                    tenant_id TEXT NOT NULL,
                    decision_id TEXT NOT NULL,
                    source_scope_id TEXT NOT NULL,
                    target_scope_id TEXT NOT NULL,
                    consequence_scope_ids_json TEXT NOT NULL,
                    impact_score REAL NOT NULL,
                    uncertainty REAL NOT NULL,
                    required_authority_scope_id TEXT,
                    disposition TEXT NOT NULL,
                    reason_codes_json TEXT NOT NULL,
                    context_sha256 TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    record_sha256 TEXT NOT NULL,
                    PRIMARY KEY (tenant_id, decision_id)
                );
                CREATE TABLE IF NOT EXISTS federation_escalations (
                    tenant_id TEXT NOT NULL,
                    escalation_id TEXT NOT NULL,
                    decision_id TEXT NOT NULL,
                    source_scope_id TEXT NOT NULL,
                    target_scope_id TEXT NOT NULL,
                    severity TEXT NOT NULL,
                    reason TEXT NOT NULL,
                    evidence_sha256_json TEXT NOT NULL,
                    opened_at TEXT NOT NULL,
                    record_sha256 TEXT NOT NULL,
                    PRIMARY KEY (tenant_id, escalation_id)
                );
                CREATE TABLE IF NOT EXISTS federation_escalation_events (
                    sequence INTEGER PRIMARY KEY AUTOINCREMENT,
                    tenant_id TEXT NOT NULL,
                    escalation_id TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    actor_id TEXT NOT NULL,
                    note TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    event_sha256 TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS federation_projection_lookup
                    ON federation_projections(tenant_id, target_scope_id, created_at);
                CREATE INDEX IF NOT EXISTS federation_escalation_lookup
                    ON federation_escalations(tenant_id, target_scope_id, opened_at);
                """
            )
            for table in (
                "federation_scopes", "federation_projections", "federation_routes",
                "federation_escalations", "federation_escalation_events",
            ):
                connection.executescript(
                    f"""
                    CREATE TRIGGER IF NOT EXISTS {table}_no_update
                    BEFORE UPDATE ON {table} BEGIN
                        SELECT RAISE(ABORT, '{table} records are immutable');
                    END;
                    CREATE TRIGGER IF NOT EXISTS {table}_no_delete
                    BEFORE DELETE ON {table} BEGIN
                        SELECT RAISE(ABORT, '{table} records are immutable');
                    END;
                    """
                )
        self.path.chmod(0o600)

    @staticmethod
    def _decode_scope(row: sqlite3.Row) -> dict[str, Any]:
        result = dict(row)
        result["data_policy"] = json.loads(result.pop("data_policy_json"))
        result["binding_authority"] = False
        return result

    def register_scope(
        self,
        tenant_id: str,
        scope_id: str,
        scope_type: str,
        name: str,
        *,
        parent_scope_id: str | None = None,
        world_id: str | None = None,
        authority_domain: str = "institutional-operations",
        decision_latency_class: str = "MINUTES",
        data_policy: dict[str, Any] | None = None,
        created_at: str | None = None,
    ) -> dict[str, Any]:
        tenant_id = _identifier(tenant_id, "tenant_id")
        scope_id = _identifier(scope_id, "scope_id")
        scope_type = str(scope_type).upper()
        if scope_type not in SCOPE_RANK:
            raise FederationError(f"unsupported scope_type: {scope_type}")
        latency = str(decision_latency_class).upper()
        if latency not in LATENCY_CLASSES:
            raise FederationError(f"unsupported decision_latency_class: {latency}")
        parent_scope_id = _identifier(parent_scope_id, "parent_scope_id") if parent_scope_id else None
        world_id = _identifier(world_id, "world_id") if world_id else None
        policy = dict(data_policy or {})
        if policy.get("share_raw_records") is True:
            raise FederationError("federation scopes cannot authorize raw-record sharing")
        policy.setdefault("share_raw_records", False)
        policy.setdefault("projection_mode", "AGGREGATES_ONLY")
        policy_json = _json(policy, "data_policy")
        at = str(created_at or _now())
        if scope_type == "GLOBAL" and parent_scope_id is not None:
            raise FederationError("GLOBAL scope cannot have a parent")
        if scope_type != "GLOBAL" and parent_scope_id is None:
            raise FederationError("non-GLOBAL scope requires a parent")
        with self._connection() as connection:
            if parent_scope_id:
                parent = connection.execute(
                    "SELECT * FROM federation_scopes WHERE tenant_id = ? AND scope_id = ?",
                    (tenant_id, parent_scope_id),
                ).fetchone()
                if parent is None:
                    raise FederationError("parent scope does not exist for tenant")
                if SCOPE_RANK[scope_type] <= SCOPE_RANK[parent["scope_type"]]:
                    raise FederationError("child scope must be below its parent in the hierarchy")
            elif connection.execute(
                "SELECT 1 FROM federation_scopes WHERE tenant_id = ? AND parent_scope_id IS NULL",
                (tenant_id,),
            ).fetchone():
                raise FederationError("tenant already has a root scope")
            record = {
                "tenant_id": tenant_id,
                "scope_id": scope_id,
                "parent_scope_id": parent_scope_id,
                "scope_type": scope_type,
                "world_id": world_id,
                "name": _identifier(name, "name"),
                "authority_domain": _identifier(authority_domain, "authority_domain"),
                "decision_latency_class": latency,
                "data_policy": json.loads(policy_json),
                "created_at": at,
            }
            record_sha256 = sha256_json(record)
            try:
                connection.execute(
                    """INSERT INTO federation_scopes
                       (tenant_id, scope_id, parent_scope_id, scope_type, world_id, name,
                        authority_domain, decision_latency_class, data_policy_json,
                        created_at, record_sha256)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        tenant_id, scope_id, parent_scope_id, scope_type, world_id,
                        record["name"], record["authority_domain"], latency, policy_json,
                        at, record_sha256,
                    ),
                )
            except sqlite3.IntegrityError as exc:
                raise FederationError("scope identity or world binding already exists") from exc
        return {**record, "record_sha256": record_sha256, "binding_authority": False}

    def get_scope(self, tenant_id: str, scope_id: str) -> dict[str, Any]:
        with self._connection() as connection:
            row = connection.execute(
                "SELECT * FROM federation_scopes WHERE tenant_id = ? AND scope_id = ?",
                (tenant_id, scope_id),
            ).fetchone()
        if row is None:
            raise FederationError("scope not found")
        return self._decode_scope(row)

    def list_scopes(self, tenant_id: str) -> list[dict[str, Any]]:
        with self._connection() as connection:
            rows = connection.execute(
                "SELECT * FROM federation_scopes WHERE tenant_id = ? ORDER BY scope_type, scope_id",
                (tenant_id,),
            ).fetchall()
        return [self._decode_scope(row) for row in rows]

    def _ancestor_ids(self, tenant_id: str, scope_id: str) -> list[str]:
        result: list[str] = []
        current: str | None = scope_id
        while current is not None:
            scope = self.get_scope(tenant_id, current)
            result.append(current)
            current = scope["parent_scope_id"]
        return result

    def least_common_ancestor(self, tenant_id: str, scope_ids: Iterable[str]) -> str:
        normalized = [_identifier(value, "scope_id") for value in scope_ids]
        if not normalized:
            raise FederationError("at least one scope is required")
        paths = [self._ancestor_ids(tenant_id, scope_id) for scope_id in normalized]
        common = set(paths[0]).intersection(*paths[1:])
        if not common:
            raise FederationError("scopes do not share a tenant root")
        return min(common, key=lambda candidate: paths[0].index(candidate))

    @staticmethod
    def _summarize_operations(scope_id: str, snapshot: dict[str, Any], at: str) -> dict[str, Any]:
        operations = snapshot["state"].get("operations", {})
        if not isinstance(operations, dict):
            operations = {}
        resources: dict[str, dict[str, Any]] = {}
        for resource_id, resource in sorted(operations.get("resource_pools", {}).items()):
            capacity = float(resource.get("capacity", 0))
            allocated = float(resource.get("allocated", 0))
            resources[resource_id] = {
                "unit": str(resource.get("unit", "unit")),
                "capacity": capacity,
                "allocated": allocated,
                "available": max(0.0, capacity - allocated),
                "utilization": allocated / capacity if capacity > 0 else 0.0,
            }
        outcomes = operations.get("outcomes", {})
        return {
            "schema_version": "edon-federation-projection.v1",
            "scope_id": scope_id,
            "projection_kind": "WORLD_SUMMARY",
            "source_world_id": snapshot["world_id"],
            "source_world_version": snapshot["version"],
            "source_state_sha256": snapshot["state_sha256"],
            "observed_at": at,
            "counts": {
                "observations": len(operations.get("observations", [])),
                "goals": _counts(operations.get("goals", {}), "status"),
                "plans": _counts(operations.get("plans", {}), "status"),
                "agents": _counts(operations.get("agents", {}), "status"),
                "alerts": _counts(operations.get("alerts", {}), "type"),
                "outcomes": {
                    "succeeded": sum(bool(row.get("success")) for row in outcomes.values()),
                    "failed": sum(not bool(row.get("success")) for row in outcomes.values()),
                },
            },
            "resources": resources,
            "contains_raw_records": False,
            "binding_authority": False,
        }

    def _insert_projection(
        self,
        tenant_id: str,
        projection_id: str,
        kind: str,
        source_scope_id: str,
        target_scope_id: str,
        summary: dict[str, Any],
        *,
        source_world_id: str | None,
        source_world_version: int | None,
        source_state_sha256: str | None,
        created_at: str,
    ) -> dict[str, Any]:
        summary_json = _json(summary, "summary")
        digest = sha256_json(summary)
        with self._connection() as connection:
            try:
                connection.execute(
                    """INSERT INTO federation_projections
                       (tenant_id, projection_id, projection_kind, source_scope_id,
                        target_scope_id, source_world_id, source_world_version,
                        source_state_sha256, summary_json, summary_sha256, created_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        tenant_id, projection_id, kind, source_scope_id, target_scope_id,
                        source_world_id, source_world_version, source_state_sha256,
                        summary_json, digest, created_at,
                    ),
                )
            except sqlite3.IntegrityError as exc:
                raise FederationError("projection identity already exists") from exc
        return {
            "tenant_id": tenant_id,
            "projection_id": projection_id,
            "projection_kind": kind,
            "source_scope_id": source_scope_id,
            "target_scope_id": target_scope_id,
            "summary": summary,
            "summary_sha256": digest,
            "created_at": created_at,
            "binding_authority": False,
        }

    def project_world(
        self,
        tenant_id: str,
        scope_id: str,
        projection_id: str,
        *,
        target_scope_id: str | None = None,
        created_at: str | None = None,
    ) -> dict[str, Any]:
        scope = self.get_scope(tenant_id, scope_id)
        if not scope["world_id"]:
            raise FederationError("scope has no bound institutional world")
        target = target_scope_id or scope["parent_scope_id"] or scope_id
        if target not in self._ancestor_ids(tenant_id, scope_id):
            raise FederationError("projection target must be the source scope or an ancestor")
        snapshot = self.worlds.get_world(tenant_id, scope["world_id"])
        at = str(created_at or _now())
        summary = self._summarize_operations(scope_id, snapshot, at)
        return self._insert_projection(
            tenant_id, _identifier(projection_id, "projection_id"), "WORLD_SUMMARY",
            scope_id, target, summary, source_world_id=snapshot["world_id"],
            source_world_version=snapshot["version"],
            source_state_sha256=snapshot["state_sha256"], created_at=at,
        )

    def _projection_rows(
        self, tenant_id: str, target_scope_id: str, source_scope_ids: Iterable[str]
    ) -> list[sqlite3.Row]:
        rows: list[sqlite3.Row] = []
        with self._connection() as connection:
            for source_scope_id in source_scope_ids:
                row = connection.execute(
                    """SELECT * FROM federation_projections
                       WHERE tenant_id = ? AND target_scope_id = ? AND source_scope_id = ?
                       ORDER BY created_at DESC, projection_id DESC LIMIT 1""",
                    (tenant_id, target_scope_id, source_scope_id),
                ).fetchone()
                if row is None:
                    raise FederationError(f"no projection available for source scope {source_scope_id}")
                rows.append(row)
        return rows

    def aggregate_scope(
        self,
        tenant_id: str,
        target_scope_id: str,
        projection_id: str,
        source_scope_ids: Iterable[str],
        *,
        publish_to_scope_id: str | None = None,
        created_at: str | None = None,
    ) -> dict[str, Any]:
        self.get_scope(tenant_id, target_scope_id)
        publish_target = publish_to_scope_id or target_scope_id
        if publish_target not in self._ancestor_ids(tenant_id, target_scope_id):
            raise FederationError("aggregate publication target must be its scope or an ancestor")
        sources = sorted({_identifier(value, "source_scope_id") for value in source_scope_ids})
        if not sources:
            raise FederationError("aggregate projection requires source scopes")
        for source in sources:
            if target_scope_id not in self._ancestor_ids(tenant_id, source):
                raise FederationError("aggregate source must descend from target scope")
        rows = self._projection_rows(tenant_id, target_scope_id, sources)
        aggregate_counts: dict[str, Any] = {
            "observations": 0, "goals": {}, "plans": {}, "agents": {}, "alerts": {},
            "outcomes": {"succeeded": 0, "failed": 0},
        }
        resources: dict[str, dict[str, Any]] = {}
        source_hashes: list[str] = []
        for row in rows:
            summary = json.loads(row["summary_json"])
            source_hashes.append(row["summary_sha256"])
            counts = summary["counts"]
            aggregate_counts["observations"] += int(counts.get("observations", 0))
            for category in ("goals", "plans", "agents", "alerts", "outcomes"):
                for key, value in counts.get(category, {}).items():
                    aggregate_counts[category][key] = aggregate_counts[category].get(key, 0) + int(value)
            for resource_id, resource in summary.get("resources", {}).items():
                current = resources.setdefault(
                    resource_id,
                    {"unit": resource["unit"], "capacity": 0.0, "allocated": 0.0},
                )
                if current["unit"] != resource["unit"]:
                    raise FederationError("resource units conflict across projections")
                current["capacity"] += float(resource["capacity"])
                current["allocated"] += float(resource["allocated"])
        for resource in resources.values():
            resource["available"] = max(0.0, resource["capacity"] - resource["allocated"])
            resource["utilization"] = (
                resource["allocated"] / resource["capacity"] if resource["capacity"] else 0.0
            )
        at = str(created_at or _now())
        summary = {
            "schema_version": "edon-federation-projection.v1",
            "scope_id": target_scope_id,
            "projection_kind": "AGGREGATE_SUMMARY",
            "source_scope_ids": sources,
            "source_projection_hashes": source_hashes,
            "observed_at": at,
            "counts": aggregate_counts,
            "resources": resources,
            "contains_raw_records": False,
            "binding_authority": False,
        }
        return self._insert_projection(
            tenant_id, _identifier(projection_id, "projection_id"), "AGGREGATE_SUMMARY",
            target_scope_id, publish_target, summary, source_world_id=None,
            source_world_version=None, source_state_sha256=None, created_at=at,
        )

    def route_decision(
        self,
        tenant_id: str,
        decision_id: str,
        source_scope_id: str,
        consequence_scope_ids: Iterable[str],
        *,
        impact_score: float,
        uncertainty: float,
        context: dict[str, Any],
        required_authority_scope_id: str | None = None,
        local_impact_threshold: float = 0.35,
        local_uncertainty_threshold: float = 0.25,
        escalation_id: str | None = None,
        severity: str = "MEDIUM",
        reason: str = "Decision exceeded local coordination boundary.",
        evidence_sha256: Iterable[str] = (),
        created_at: str | None = None,
    ) -> dict[str, Any]:
        tenant_id = _identifier(tenant_id, "tenant_id")
        decision_id = _identifier(decision_id, "decision_id")
        source_scope_id = _identifier(source_scope_id, "source_scope_id")
        self.get_scope(tenant_id, source_scope_id)
        consequences = sorted({_identifier(value, "consequence_scope_id") for value in consequence_scope_ids})
        scope_set = [source_scope_id, *consequences]
        target = self.least_common_ancestor(tenant_id, scope_set)
        reasons: list[str] = []
        if target != source_scope_id:
            reasons.append("CROSS_SCOPE_CONSEQUENCE")
        impact = _score(impact_score, "impact_score")
        uncertainty_value = _score(uncertainty, "uncertainty")
        if impact >= _score(local_impact_threshold, "local_impact_threshold"):
            reasons.append("IMPACT_THRESHOLD_EXCEEDED")
        if uncertainty_value >= _score(local_uncertainty_threshold, "local_uncertainty_threshold"):
            reasons.append("UNCERTAINTY_THRESHOLD_EXCEEDED")
        authority = _identifier(required_authority_scope_id, "required_authority_scope_id") if required_authority_scope_id else None
        if authority:
            self.get_scope(tenant_id, authority)
            target = self.least_common_ancestor(tenant_id, [target, authority])
            if authority != source_scope_id:
                reasons.append("HIGHER_AUTHORITY_REQUIRED")
        source = self.get_scope(tenant_id, source_scope_id)
        if reasons and target == source_scope_id and source["parent_scope_id"]:
            target = source["parent_scope_id"]
        disposition = "HANDLE_LOCAL" if target == source_scope_id and not reasons else (
            "HANDLE_AT_ROOT" if target == source_scope_id else "ESCALATE"
        )
        at = str(created_at or _now())
        route = {
            "tenant_id": tenant_id,
            "decision_id": decision_id,
            "source_scope_id": source_scope_id,
            "target_scope_id": target,
            "consequence_scope_ids": consequences,
            "impact_score": impact,
            "uncertainty": uncertainty_value,
            "required_authority_scope_id": authority,
            "disposition": disposition,
            "reason_codes": sorted(set(reasons)) or ["WITHIN_LOCAL_BOUNDARY"],
            "context_sha256": sha256_json(context),
            "created_at": at,
            "binding_authority": False,
        }
        route_sha = sha256_json(route)
        with self._connection() as connection:
            try:
                connection.execute(
                    """INSERT INTO federation_routes
                       (tenant_id, decision_id, source_scope_id, target_scope_id,
                        consequence_scope_ids_json, impact_score, uncertainty,
                        required_authority_scope_id, disposition, reason_codes_json,
                        context_sha256, created_at, record_sha256)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        tenant_id, decision_id, source_scope_id, target,
                        json.dumps(consequences), impact, uncertainty_value, authority,
                        disposition, json.dumps(route["reason_codes"]), route["context_sha256"],
                        at, route_sha,
                    ),
                )
            except sqlite3.IntegrityError as exc:
                raise FederationError("decision identity already exists") from exc
        result = {**route, "record_sha256": route_sha}
        if disposition == "ESCALATE":
            result["escalation"] = self.open_escalation(
                tenant_id, escalation_id or f"escalation-{decision_id}", decision_id,
                source_scope_id, target, severity=severity, reason=reason,
                evidence_sha256=evidence_sha256, opened_at=at,
            )
        return result

    def open_escalation(
        self,
        tenant_id: str,
        escalation_id: str,
        decision_id: str,
        source_scope_id: str,
        target_scope_id: str,
        *,
        severity: str,
        reason: str,
        evidence_sha256: Iterable[str] = (),
        opened_at: str | None = None,
    ) -> dict[str, Any]:
        severity = str(severity).upper()
        if severity not in SEVERITIES:
            raise FederationError(f"unsupported escalation severity: {severity}")
        evidence = sorted({_identifier(value, "evidence_sha256") for value in evidence_sha256})
        at = str(opened_at or _now())
        record = {
            "tenant_id": _identifier(tenant_id, "tenant_id"),
            "escalation_id": _identifier(escalation_id, "escalation_id"),
            "decision_id": _identifier(decision_id, "decision_id"),
            "source_scope_id": _identifier(source_scope_id, "source_scope_id"),
            "target_scope_id": _identifier(target_scope_id, "target_scope_id"),
            "severity": severity,
            "reason": str(reason).strip(),
            "evidence_sha256": evidence,
            "opened_at": at,
            "binding_authority": False,
        }
        if not record["reason"]:
            raise FederationError("escalation reason is required")
        digest = sha256_json(record)
        with self._connection() as connection:
            try:
                connection.execute(
                    """INSERT INTO federation_escalations
                       (tenant_id, escalation_id, decision_id, source_scope_id,
                        target_scope_id, severity, reason, evidence_sha256_json,
                        opened_at, record_sha256)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        record["tenant_id"], record["escalation_id"], record["decision_id"],
                        record["source_scope_id"], record["target_scope_id"], severity,
                        record["reason"], json.dumps(evidence), at, digest,
                    ),
                )
            except sqlite3.IntegrityError as exc:
                raise FederationError("escalation identity already exists") from exc
        self.record_escalation_event(
            record["tenant_id"], record["escalation_id"], "OPENED", "federation-router",
            record["reason"], created_at=at,
        )
        return {**record, "record_sha256": digest, "status": "OPEN"}

    def record_escalation_event(
        self,
        tenant_id: str,
        escalation_id: str,
        event_type: str,
        actor_id: str,
        note: str,
        *,
        created_at: str | None = None,
    ) -> dict[str, Any]:
        event_type = str(event_type).upper()
        if event_type not in {"OPENED", "ACKNOWLEDGED", "RESOLVED", "REJECTED"}:
            raise FederationError("unsupported escalation event type")
        at = str(created_at or _now())
        event = {
            "tenant_id": _identifier(tenant_id, "tenant_id"),
            "escalation_id": _identifier(escalation_id, "escalation_id"),
            "event_type": event_type,
            "actor_id": _identifier(actor_id, "actor_id"),
            "note": str(note).strip(),
            "created_at": at,
        }
        if not event["note"]:
            raise FederationError("escalation event note is required")
        with self._connection() as connection:
            if connection.execute(
                "SELECT 1 FROM federation_escalations WHERE tenant_id = ? AND escalation_id = ?",
                (event["tenant_id"], event["escalation_id"]),
            ).fetchone() is None:
                raise FederationError("escalation not found")
            event_sha = sha256_json(event)
            connection.execute(
                """INSERT INTO federation_escalation_events
                   (tenant_id, escalation_id, event_type, actor_id, note, created_at, event_sha256)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (
                    event["tenant_id"], event["escalation_id"], event_type,
                    event["actor_id"], event["note"], at, event_sha,
                ),
            )
        return {**event, "event_sha256": event_sha, "binding_authority": False}

    def list_escalations(self, tenant_id: str, target_scope_id: str | None = None) -> list[dict[str, Any]]:
        query = "SELECT * FROM federation_escalations WHERE tenant_id = ?"
        parameters: list[Any] = [tenant_id]
        if target_scope_id:
            query += " AND target_scope_id = ?"
            parameters.append(target_scope_id)
        query += " ORDER BY opened_at, escalation_id"
        with self._connection() as connection:
            rows = connection.execute(query, parameters).fetchall()
            result = []
            for row in rows:
                events = connection.execute(
                    """SELECT event_type, actor_id, note, created_at, event_sha256
                       FROM federation_escalation_events
                       WHERE tenant_id = ? AND escalation_id = ? ORDER BY sequence""",
                    (tenant_id, row["escalation_id"]),
                ).fetchall()
                item = dict(row)
                item["evidence_sha256"] = json.loads(item.pop("evidence_sha256_json"))
                item["events"] = [dict(event) for event in events]
                item["status"] = events[-1]["event_type"] if events else "OPENED"
                item["binding_authority"] = False
                result.append(item)
        return result

    def counts(self) -> dict[str, int]:
        with self._connection() as connection:
            return {
                "scopes": connection.execute("SELECT COUNT(*) FROM federation_scopes").fetchone()[0],
                "projections": connection.execute("SELECT COUNT(*) FROM federation_projections").fetchone()[0],
                "routes": connection.execute("SELECT COUNT(*) FROM federation_routes").fetchone()[0],
                "escalations": connection.execute("SELECT COUNT(*) FROM federation_escalations").fetchone()[0],
            }