"""Persistent governed product services for ActionNet institutional experience."""

from __future__ import annotations

import json
import math
import sqlite3
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Iterable

from edon.common.hashing import canonical_json, sha256_json

from .institutional import InstitutionalIRValidator
from .intake import GovernedAbstractionValidator


class ActionNetPlatformError(RuntimeError):
    """Raised when an ActionNet product record violates governance controls."""


EVIDENCE_GRADES = {
    "UNVERIFIED",
    "SYNTHETIC_VERIFIED",
    "SOLVER_VERIFIED",
    "EXPERT_REVIEWED",
    "SOURCE_GROUNDED",
    "REAL_OUTCOME",
}
SOURCE_TYPES = {
    "SYNTHETIC",
    "SIMULATOR",
    "SOLVER",
    "EXPERT",
    "PUBLIC_SOURCE",
    "REAL_GOVERNED_ABSTRACTION",
}
COMPOSITION_RELATIONS = {
    "COMPOSES_WITH",
    "AMPLIFIES",
    "MITIGATES",
    "INHIBITS",
    "PRECONDITION_FOR",
    "CAUSES",
    "ABSTRACTS_TO",
}
REVIEW_DIMENSIONS = {"DOMAIN", "SAFETY", "PRIVACY", "LINEAGE", "TRAINING"}
REVIEW_DECISIONS = {"APPROVE", "REJECT", "REVISION_REQUIRED"}
EXPOSURE_PURPOSES = {"TRAIN", "DEVELOPMENT", "DIAGNOSTIC", "PROTECTED_EVALUATION"}
REVIEW_ROLE_REQUIREMENTS = {
    "DOMAIN": {"DOMAIN_REVIEWER", "ACTIONNET_DOMAIN_REVIEWER", "ADMIN"},
    "SAFETY": {"SAFETY_REVIEWER", "ACTIONNET_SAFETY_REVIEWER", "ADMIN"},
    "PRIVACY": {"ACTIONNET_PRIVACY_REVIEWER", "ADMIN"},
    "LINEAGE": {"ACTIONNET_CUSTODIAN", "ADMIN"},
    "TRAINING": {"ACTIONNET_RELEASE_MANAGER", "ADMIN"},
}


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _identifier(value: Any, label: str) -> str:
    normalized = str(value).strip()
    if not normalized or len(normalized) > 200:
        raise ActionNetPlatformError(f"{label} must contain between 1 and 200 characters")
    return normalized


def _text(value: Any, label: str, *, minimum: int = 1, maximum: int = 20_000) -> str:
    normalized = str(value).strip()
    if len(normalized) < minimum or len(normalized) > maximum:
        raise ActionNetPlatformError(
            f"{label} must contain between {minimum} and {maximum} characters"
        )
    return normalized


def _score(value: Any, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ActionNetPlatformError(f"{label} must be numeric")
    result = float(value)
    if not math.isfinite(result) or not 0 <= result <= 1:
        raise ActionNetPlatformError(f"{label} must be between 0 and 1")
    return result


def _json_object(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ActionNetPlatformError(f"{label} must be a JSON object")
    try:
        json.dumps(value, allow_nan=False)
    except (TypeError, ValueError) as exc:
        raise ActionNetPlatformError(f"{label} must contain finite JSON values") from exc
    return json.loads(json.dumps(value))


def _string_list(values: Iterable[Any], label: str) -> list[str]:
    return sorted({_identifier(value, label) for value in values})


def _forbid_authority(value: Any, path: str = "record") -> None:
    forbidden = {
        "authorization_ref", "execution_token", "kernel_token", "signature",
        "binding_authority", "commit", "approved_for_execution", "execute",
    }
    if isinstance(value, dict):
        for key, nested in value.items():
            normalized_key = str(key).lower()
            if normalized_key == "binding_authority" and nested is False:
                continue
            if normalized_key in forbidden:
                raise ActionNetPlatformError(f"ActionNet product record cannot contain {path}.{key}")
            _forbid_authority(nested, f"{path}.{key}")
    elif isinstance(value, list):
        for index, nested in enumerate(value):
            _forbid_authority(nested, f"{path}[{index}]")


class ActionNetPlatformStore:
    """Tenant-isolated, append-only ActionNet product registry and experience ledger."""

    def __init__(self, path: Path | str):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA journal_mode = WAL")
        connection.execute("PRAGMA synchronous = FULL")
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
                CREATE TABLE IF NOT EXISTS actionnet_product_metadata (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS actionnet_mechanisms (
                    tenant_id TEXT NOT NULL,
                    mechanism_id TEXT NOT NULL,
                    version TEXT NOT NULL,
                    title TEXT NOT NULL,
                    description TEXT NOT NULL,
                    specification_json TEXT NOT NULL,
                    domains_json TEXT NOT NULL,
                    evidence_grade TEXT NOT NULL,
                    source_lineage_json TEXT NOT NULL,
                    created_by TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    record_sha256 TEXT NOT NULL,
                    PRIMARY KEY (tenant_id, mechanism_id, version)
                );
                CREATE TABLE IF NOT EXISTS actionnet_institutional_ir (
                    tenant_id TEXT NOT NULL,
                    institution_id TEXT NOT NULL,
                    version TEXT NOT NULL,
                    institution_type TEXT NOT NULL,
                    ir_json TEXT NOT NULL,
                    source_lineage_json TEXT NOT NULL,
                    protected INTEGER NOT NULL,
                    created_by TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    record_sha256 TEXT NOT NULL,
                    PRIMARY KEY (tenant_id, institution_id, version)
                );
                CREATE TABLE IF NOT EXISTS actionnet_composition_edges (
                    tenant_id TEXT NOT NULL,
                    edge_id TEXT NOT NULL,
                    source_mechanism_id TEXT NOT NULL,
                    source_version TEXT NOT NULL,
                    target_mechanism_id TEXT NOT NULL,
                    target_version TEXT NOT NULL,
                    relation_type TEXT NOT NULL,
                    conditions_json TEXT NOT NULL,
                    evidence_grade TEXT NOT NULL,
                    provenance_json TEXT NOT NULL,
                    created_by TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    record_sha256 TEXT NOT NULL,
                    PRIMARY KEY (tenant_id, edge_id)
                );
                CREATE TABLE IF NOT EXISTS actionnet_world_blueprints (
                    tenant_id TEXT NOT NULL,
                    blueprint_id TEXT NOT NULL,
                    version TEXT NOT NULL,
                    blueprint_json TEXT NOT NULL,
                    generator_seed INTEGER,
                    adversarial INTEGER NOT NULL,
                    protected INTEGER NOT NULL,
                    created_by TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    record_sha256 TEXT NOT NULL,
                    PRIMARY KEY (tenant_id, blueprint_id, version)
                );
                CREATE TABLE IF NOT EXISTS actionnet_experiences (
                    tenant_id TEXT NOT NULL,
                    experience_id TEXT NOT NULL,
                    source_type TEXT NOT NULL,
                    institution_type TEXT NOT NULL,
                    mechanism_refs_json TEXT NOT NULL,
                    trajectory_json TEXT NOT NULL,
                    causal_trace_json TEXT NOT NULL,
                    counterfactual_parent_id TEXT,
                    failure_classification TEXT,
                    evidence_grade TEXT NOT NULL,
                    protected INTEGER NOT NULL,
                    provenance_json TEXT NOT NULL,
                    created_by TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    content_sha256 TEXT NOT NULL,
                    PRIMARY KEY (tenant_id, experience_id)
                );
                CREATE TABLE IF NOT EXISTS actionnet_experience_reviews (
                    tenant_id TEXT NOT NULL,
                    review_id TEXT NOT NULL,
                    experience_id TEXT NOT NULL,
                    reviewer_id TEXT NOT NULL,
                    reviewer_role TEXT NOT NULL,
                    dimension TEXT NOT NULL,
                    decision TEXT NOT NULL,
                    rationale TEXT NOT NULL,
                    experience_sha256 TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    review_sha256 TEXT NOT NULL,
                    PRIMARY KEY (tenant_id, review_id),
                    UNIQUE (tenant_id, experience_id, reviewer_id, dimension)
                );
                CREATE TABLE IF NOT EXISTS actionnet_governance_events (
                    sequence INTEGER PRIMARY KEY AUTOINCREMENT,
                    tenant_id TEXT NOT NULL,
                    experience_id TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    actor_id TEXT NOT NULL,
                    details_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    event_sha256 TEXT NOT NULL UNIQUE
                );
                CREATE TABLE IF NOT EXISTS actionnet_model_exposures (
                    tenant_id TEXT NOT NULL,
                    exposure_id TEXT NOT NULL,
                    experience_id TEXT NOT NULL,
                    model_id TEXT NOT NULL,
                    dataset_release_id TEXT,
                    purpose TEXT NOT NULL,
                    created_by TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    record_sha256 TEXT NOT NULL,
                    PRIMARY KEY (tenant_id, exposure_id),
                    UNIQUE (tenant_id, experience_id, model_id, purpose)
                );
                CREATE TABLE IF NOT EXISTS actionnet_coverage_snapshots (
                    tenant_id TEXT NOT NULL,
                    snapshot_id TEXT NOT NULL,
                    report_json TEXT NOT NULL,
                    registered_universe_json TEXT NOT NULL,
                    created_by TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    report_sha256 TEXT NOT NULL,
                    PRIMARY KEY (tenant_id, snapshot_id)
                );
                CREATE TABLE IF NOT EXISTS actionnet_acquisition_recommendations (
                    tenant_id TEXT NOT NULL,
                    recommendation_id TEXT NOT NULL,
                    target_mechanism_ids_json TEXT NOT NULL,
                    gap_dimensions_json TEXT NOT NULL,
                    rationale TEXT NOT NULL,
                    priority REAL NOT NULL,
                    expected_information_gain REAL NOT NULL,
                    evidence_json TEXT NOT NULL,
                    created_by TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    record_sha256 TEXT NOT NULL,
                    PRIMARY KEY (tenant_id, recommendation_id)
                );
                CREATE TABLE IF NOT EXISTS actionnet_intervention_candidates (
                    tenant_id TEXT NOT NULL,
                    intervention_id TEXT NOT NULL,
                    scope_id TEXT NOT NULL,
                    source_experience_ids_json TEXT NOT NULL,
                    action_json TEXT NOT NULL,
                    objectives_json TEXT NOT NULL,
                    constraints_json TEXT NOT NULL,
                    predicted_outcomes_json TEXT NOT NULL,
                    verification_json TEXT NOT NULL,
                    confidence REAL NOT NULL,
                    created_by TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    record_sha256 TEXT NOT NULL,
                    PRIMARY KEY (tenant_id, intervention_id)
                );
                CREATE TABLE IF NOT EXISTS actionnet_training_releases (
                    tenant_id TEXT NOT NULL,
                    release_id TEXT NOT NULL,
                    experience_ids_json TEXT NOT NULL,
                    experience_hashes_json TEXT NOT NULL,
                    model_target TEXT NOT NULL,
                    release_manager_id TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    release_sha256 TEXT NOT NULL,
                    PRIMARY KEY (tenant_id, release_id)
                );
                CREATE TABLE IF NOT EXISTS actionnet_composition_runs (
                    tenant_id TEXT NOT NULL,
                    run_id TEXT NOT NULL,
                    institution_id TEXT NOT NULL,
                    institution_version TEXT NOT NULL,
                    run_json TEXT NOT NULL,
                    protected INTEGER NOT NULL,
                    created_by TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    record_sha256 TEXT NOT NULL,
                    PRIMARY KEY (tenant_id, run_id)
                );
                CREATE TABLE IF NOT EXISTS actionnet_counterfactual_batches (
                    tenant_id TEXT NOT NULL,
                    batch_id TEXT NOT NULL,
                    parent_experience_id TEXT NOT NULL,
                    batch_json TEXT NOT NULL,
                    child_experience_ids_json TEXT NOT NULL,
                    protected INTEGER NOT NULL,
                    created_by TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    record_sha256 TEXT NOT NULL,
                    PRIMARY KEY (tenant_id, batch_id)
                );
                CREATE TABLE IF NOT EXISTS actionnet_behavior_scenarios (
                    tenant_id TEXT NOT NULL,
                    scenario_id TEXT NOT NULL,
                    institution_id TEXT NOT NULL,
                    institution_version TEXT NOT NULL,
                    scenario_json TEXT NOT NULL,
                    protected INTEGER NOT NULL,
                    created_by TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    record_sha256 TEXT NOT NULL,
                    PRIMARY KEY (tenant_id, scenario_id)
                );
                CREATE TABLE IF NOT EXISTS actionnet_governed_intakes (
                    tenant_id TEXT NOT NULL,
                    intake_id TEXT NOT NULL,
                    institution_id TEXT NOT NULL,
                    institution_version TEXT NOT NULL,
                    experience_id TEXT NOT NULL,
                    abstraction_json TEXT NOT NULL,
                    created_by TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    record_sha256 TEXT NOT NULL,
                    PRIMARY KEY (tenant_id, intake_id),
                    UNIQUE (tenant_id, experience_id)
                );
                CREATE TABLE IF NOT EXISTS actionnet_product_audit (
                    sequence INTEGER PRIMARY KEY AUTOINCREMENT,
                    tenant_id TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    entity_id TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    previous_hash TEXT NOT NULL,
                    event_hash TEXT NOT NULL UNIQUE,
                    created_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS actionnet_experience_mechanism_lookup
                    ON actionnet_experiences(tenant_id, evidence_grade, protected);
                CREATE INDEX IF NOT EXISTS actionnet_review_lookup
                    ON actionnet_experience_reviews(tenant_id, experience_id, dimension);
                CREATE INDEX IF NOT EXISTS actionnet_governance_lookup
                    ON actionnet_governance_events(tenant_id, experience_id, sequence);
                """
            )
            connection.execute(
                """INSERT INTO actionnet_product_metadata(key, value)
                   VALUES ('schema_version', 'actionnet-platform-store.v2')
                   ON CONFLICT(key) DO UPDATE SET value = excluded.value"""
            )
            immutable_tables = (
                "actionnet_mechanisms", "actionnet_institutional_ir",
                "actionnet_composition_edges",
                "actionnet_world_blueprints", "actionnet_experiences",
                "actionnet_experience_reviews", "actionnet_governance_events",
                "actionnet_model_exposures", "actionnet_coverage_snapshots",
                "actionnet_acquisition_recommendations", "actionnet_intervention_candidates",
                "actionnet_training_releases", "actionnet_composition_runs",
                "actionnet_counterfactual_batches", "actionnet_behavior_scenarios",
                "actionnet_governed_intakes", "actionnet_product_audit",
            )
            for table in immutable_tables:
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

    def _audit(
        self,
        connection: sqlite3.Connection,
        tenant_id: str,
        event_type: str,
        entity_id: str,
        payload: dict[str, Any],
        created_at: str,
    ) -> str:
        previous = connection.execute(
            """SELECT event_hash FROM actionnet_product_audit
               WHERE tenant_id = ? ORDER BY sequence DESC LIMIT 1""",
            (tenant_id,),
        ).fetchone()
        previous_hash = previous["event_hash"] if previous else "GENESIS"
        record = {
            "tenant_id": tenant_id,
            "event_type": event_type,
            "entity_id": entity_id,
            "payload": payload,
            "previous_hash": previous_hash,
            "created_at": created_at,
        }
        event_hash = sha256_json(record)
        connection.execute(
            """INSERT INTO actionnet_product_audit
               (tenant_id, event_type, entity_id, payload_json, previous_hash,
                event_hash, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                tenant_id, event_type, entity_id, canonical_json(payload),
                previous_hash, event_hash, created_at,
            ),
        )
        return event_hash

    @staticmethod
    def _evidence_grade(value: Any) -> str:
        grade = str(value).upper()
        if grade not in EVIDENCE_GRADES:
            raise ActionNetPlatformError(f"unsupported evidence grade: {grade}")
        return grade

    def register_institutional_ir(
        self,
        tenant_id: str,
        institution_id: str,
        version: str,
        document: dict[str, Any],
        *,
        source_lineage: Iterable[str] = (),
        protected: bool = False,
        created_by: str,
        created_at: str | None = None,
    ) -> dict[str, Any]:
        tenant_id = _identifier(tenant_id, "tenant_id")
        institution_id = _identifier(institution_id, "institution_id")
        version = _identifier(version, "version")
        normalized = InstitutionalIRValidator().normalize(
            document, institution_id=institution_id, version=version
        )
        _forbid_authority(normalized, "institutional_ir")
        lineage = _string_list(source_lineage, "source_lineage")
        at = str(created_at or _now())
        record = {
            "schema_version": "actionnet-institutional-ir-record.v1",
            "tenant_id": tenant_id,
            "institution_id": institution_id,
            "version": version,
            "institution_type": normalized["institution_type"],
            "institutional_ir": normalized,
            "source_lineage": lineage,
            "protected": bool(protected),
            "created_by": _identifier(created_by, "created_by"),
            "created_at": at,
            "authoritative": False,
            "binding_authority": False,
        }
        digest = sha256_json(record)
        with self._connection() as connection:
            try:
                connection.execute(
                    """INSERT INTO actionnet_institutional_ir
                       (tenant_id, institution_id, version, institution_type, ir_json,
                        source_lineage_json, protected, created_by, created_at, record_sha256)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        tenant_id, institution_id, version, normalized["institution_type"],
                        canonical_json(normalized), canonical_json(lineage), int(bool(protected)),
                        record["created_by"], at, digest,
                    ),
                )
            except sqlite3.IntegrityError as exc:
                raise ActionNetPlatformError("Institutional IR version already exists") from exc
            self._audit(
                connection, tenant_id, "INSTITUTIONAL_IR_REGISTERED",
                f"{institution_id}@{version}",
                {"record_sha256": digest, "ir_sha256": normalized["ir_sha256"], "protected": bool(protected)},
                at,
            )
        return {**record, "record_sha256": digest}

    def institutional_ir(
        self, tenant_id: str, institution_id: str, version: str
    ) -> dict[str, Any]:
        with self._connection() as connection:
            row = connection.execute(
                """SELECT * FROM actionnet_institutional_ir
                   WHERE tenant_id = ? AND institution_id = ? AND version = ?""",
                (tenant_id, institution_id, version),
            ).fetchone()
        if row is None:
            raise ActionNetPlatformError("Institutional IR version not found")
        return {
            "schema_version": "actionnet-institutional-ir-record.v1",
            "tenant_id": row["tenant_id"],
            "institution_id": row["institution_id"],
            "version": row["version"],
            "institution_type": row["institution_type"],
            "institutional_ir": json.loads(row["ir_json"]),
            "source_lineage": json.loads(row["source_lineage_json"]),
            "protected": bool(row["protected"]),
            "created_by": row["created_by"],
            "created_at": row["created_at"],
            "authoritative": False,
            "binding_authority": False,
            "record_sha256": row["record_sha256"],
        }

    def mechanism(self, tenant_id: str, mechanism_id: str, version: str) -> dict[str, Any]:
        with self._connection() as connection:
            row = connection.execute(
                """SELECT * FROM actionnet_mechanisms
                   WHERE tenant_id = ? AND mechanism_id = ? AND version = ?""",
                (tenant_id, mechanism_id, version),
            ).fetchone()
        if row is None:
            raise ActionNetPlatformError("mechanism version not found")
        item = dict(row)
        item["specification"] = json.loads(item.pop("specification_json"))
        item["domains"] = json.loads(item.pop("domains_json"))
        item["source_lineage"] = json.loads(item.pop("source_lineage_json"))
        item["binding_authority"] = False
        return item

    def composition_edge(self, tenant_id: str, edge_id: str) -> dict[str, Any]:
        with self._connection() as connection:
            row = connection.execute(
                """SELECT * FROM actionnet_composition_edges
                   WHERE tenant_id = ? AND edge_id = ?""",
                (tenant_id, edge_id),
            ).fetchone()
        if row is None:
            raise ActionNetPlatformError("composition edge not found")
        return {
            "edge_id": row["edge_id"],
            "source": {
                "mechanism_id": row["source_mechanism_id"], "version": row["source_version"]
            },
            "target": {
                "mechanism_id": row["target_mechanism_id"], "version": row["target_version"]
            },
            "relation_type": row["relation_type"],
            "conditions": json.loads(row["conditions_json"]),
            "evidence_grade": row["evidence_grade"],
            "provenance": json.loads(row["provenance_json"]),
            "record_sha256": row["record_sha256"],
            "binding_authority": False,
        }

    def register_mechanism(
        self,
        tenant_id: str,
        mechanism_id: str,
        version: str,
        title: str,
        description: str,
        specification: dict[str, Any],
        *,
        domains: Iterable[str] = (),
        evidence_grade: str = "UNVERIFIED",
        source_lineage: Iterable[str] = (),
        created_by: str,
        created_at: str | None = None,
    ) -> dict[str, Any]:
        tenant_id = _identifier(tenant_id, "tenant_id")
        mechanism_id = _identifier(mechanism_id, "mechanism_id")
        version = _identifier(version, "version")
        specification = _json_object(specification, "specification")
        required = {"preconditions", "state_transitions", "dependencies", "interventions", "failure_modes", "expected_outcomes"}
        missing = sorted(required - set(specification))
        if missing:
            raise ActionNetPlatformError(f"mechanism specification missing: {', '.join(missing)}")
        _forbid_authority(specification, "specification")
        domains_list = _string_list(domains, "domain")
        lineage = _string_list(source_lineage, "source_lineage")
        at = str(created_at or _now())
        record = {
            "schema_version": "actionnet-mechanism.v1",
            "tenant_id": tenant_id,
            "mechanism_id": mechanism_id,
            "version": version,
            "title": _text(title, "title", maximum=500),
            "description": _text(description, "description", minimum=10),
            "specification": specification,
            "domains": domains_list,
            "evidence_grade": self._evidence_grade(evidence_grade),
            "source_lineage": lineage,
            "created_by": _identifier(created_by, "created_by"),
            "created_at": at,
            "binding_authority": False,
        }
        digest = sha256_json(record)
        with self._connection() as connection:
            try:
                connection.execute(
                    """INSERT INTO actionnet_mechanisms
                       (tenant_id, mechanism_id, version, title, description,
                        specification_json, domains_json, evidence_grade,
                        source_lineage_json, created_by, created_at, record_sha256)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        tenant_id, mechanism_id, version, record["title"],
                        record["description"], canonical_json(specification),
                        canonical_json(domains_list), record["evidence_grade"],
                        canonical_json(lineage), record["created_by"], at, digest,
                    ),
                )
            except sqlite3.IntegrityError as exc:
                raise ActionNetPlatformError("mechanism version already exists") from exc
            self._audit(
                connection, tenant_id, "MECHANISM_REGISTERED",
                f"{mechanism_id}@{version}", {"record_sha256": digest}, at,
            )
        return {**record, "record_sha256": digest}

    def _mechanism_exists(
        self, connection: sqlite3.Connection, tenant_id: str, mechanism_id: str, version: str
    ) -> bool:
        return connection.execute(
            """SELECT 1 FROM actionnet_mechanisms
               WHERE tenant_id = ? AND mechanism_id = ? AND version = ?""",
            (tenant_id, mechanism_id, version),
        ).fetchone() is not None

    def register_composition_edge(
        self,
        tenant_id: str,
        edge_id: str,
        source_mechanism_id: str,
        source_version: str,
        target_mechanism_id: str,
        target_version: str,
        relation_type: str,
        *,
        conditions: dict[str, Any],
        evidence_grade: str,
        provenance: dict[str, Any],
        created_by: str,
        created_at: str | None = None,
    ) -> dict[str, Any]:
        tenant_id = _identifier(tenant_id, "tenant_id")
        relation = str(relation_type).upper()
        if relation not in COMPOSITION_RELATIONS:
            raise ActionNetPlatformError(f"unsupported composition relation: {relation}")
        source_mechanism_id = _identifier(source_mechanism_id, "source_mechanism_id")
        target_mechanism_id = _identifier(target_mechanism_id, "target_mechanism_id")
        source_version = _identifier(source_version, "source_version")
        target_version = _identifier(target_version, "target_version")
        conditions = _json_object(conditions, "conditions")
        provenance = _json_object(provenance, "provenance")
        at = str(created_at or _now())
        record = {
            "schema_version": "actionnet-composition-edge.v1",
            "tenant_id": tenant_id,
            "edge_id": _identifier(edge_id, "edge_id"),
            "source": {"mechanism_id": source_mechanism_id, "version": source_version},
            "target": {"mechanism_id": target_mechanism_id, "version": target_version},
            "relation_type": relation,
            "conditions": conditions,
            "evidence_grade": self._evidence_grade(evidence_grade),
            "provenance": provenance,
            "created_by": _identifier(created_by, "created_by"),
            "created_at": at,
            "binding_authority": False,
        }
        digest = sha256_json(record)
        with self._connection() as connection:
            if not self._mechanism_exists(connection, tenant_id, source_mechanism_id, source_version):
                raise ActionNetPlatformError("source mechanism version does not exist")
            if not self._mechanism_exists(connection, tenant_id, target_mechanism_id, target_version):
                raise ActionNetPlatformError("target mechanism version does not exist")
            try:
                connection.execute(
                    """INSERT INTO actionnet_composition_edges
                       (tenant_id, edge_id, source_mechanism_id, source_version,
                        target_mechanism_id, target_version, relation_type,
                        conditions_json, evidence_grade, provenance_json,
                        created_by, created_at, record_sha256)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        tenant_id, record["edge_id"], source_mechanism_id, source_version,
                        target_mechanism_id, target_version, relation,
                        canonical_json(conditions), record["evidence_grade"],
                        canonical_json(provenance), record["created_by"], at, digest,
                    ),
                )
            except sqlite3.IntegrityError as exc:
                raise ActionNetPlatformError("composition edge already exists") from exc
            self._audit(
                connection, tenant_id, "COMPOSITION_EDGE_REGISTERED", record["edge_id"],
                {"record_sha256": digest}, at,
            )
        return {**record, "record_sha256": digest}

    def register_world_blueprint(
        self,
        tenant_id: str,
        blueprint_id: str,
        version: str,
        blueprint: dict[str, Any],
        *,
        generator_seed: int | None,
        adversarial: bool,
        protected: bool,
        created_by: str,
        created_at: str | None = None,
    ) -> dict[str, Any]:
        tenant_id = _identifier(tenant_id, "tenant_id")
        blueprint = _json_object(blueprint, "blueprint")
        _forbid_authority(blueprint, "blueprint")
        at = str(created_at or _now())
        record = {
            "schema_version": "actionnet-world-blueprint.v1",
            "tenant_id": tenant_id,
            "blueprint_id": _identifier(blueprint_id, "blueprint_id"),
            "version": _identifier(version, "version"),
            "blueprint": blueprint,
            "generator_seed": int(generator_seed) if generator_seed is not None else None,
            "adversarial": bool(adversarial),
            "protected": bool(protected),
            "created_by": _identifier(created_by, "created_by"),
            "created_at": at,
            "binding_authority": False,
        }
        digest = sha256_json(record)
        with self._connection() as connection:
            try:
                connection.execute(
                    """INSERT INTO actionnet_world_blueprints
                       (tenant_id, blueprint_id, version, blueprint_json, generator_seed,
                        adversarial, protected, created_by, created_at, record_sha256)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        tenant_id, record["blueprint_id"], record["version"],
                        canonical_json(blueprint), record["generator_seed"],
                        int(record["adversarial"]), int(record["protected"]),
                        record["created_by"], at, digest,
                    ),
                )
            except sqlite3.IntegrityError as exc:
                raise ActionNetPlatformError("world blueprint version already exists") from exc
            self._audit(
                connection, tenant_id, "WORLD_BLUEPRINT_REGISTERED",
                f"{record['blueprint_id']}@{record['version']}",
                {"record_sha256": digest, "protected": protected}, at,
            )
        return {**record, "record_sha256": digest}

    def record_experience(
        self,
        tenant_id: str,
        experience_id: str,
        source_type: str,
        institution_type: str,
        mechanism_refs: Iterable[dict[str, Any]],
        trajectory: dict[str, Any],
        causal_trace: dict[str, Any],
        *,
        evidence_grade: str,
        provenance: dict[str, Any],
        created_by: str,
        counterfactual_parent_id: str | None = None,
        failure_classification: str | None = None,
        protected: bool = False,
        created_at: str | None = None,
    ) -> dict[str, Any]:
        tenant_id = _identifier(tenant_id, "tenant_id")
        source_type = str(source_type).upper()
        if source_type not in SOURCE_TYPES:
            raise ActionNetPlatformError(f"unsupported source type: {source_type}")
        trajectory = _json_object(trajectory, "trajectory")
        causal_trace = _json_object(causal_trace, "causal_trace")
        provenance = _json_object(provenance, "provenance")
        _forbid_authority(trajectory, "trajectory")
        refs: list[dict[str, str]] = []
        for raw in mechanism_refs:
            if not isinstance(raw, dict):
                raise ActionNetPlatformError("mechanism reference must be an object")
            refs.append(
                {
                    "mechanism_id": _identifier(raw.get("mechanism_id"), "mechanism_id"),
                    "version": _identifier(raw.get("version"), "mechanism version"),
                }
            )
        refs = sorted(refs, key=lambda row: (row["mechanism_id"], row["version"]))
        if not refs:
            raise ActionNetPlatformError("experience requires at least one mechanism reference")
        at = str(created_at or _now())
        record = {
            "schema_version": "actionnet-experience.v1",
            "tenant_id": tenant_id,
            "experience_id": _identifier(experience_id, "experience_id"),
            "source_type": source_type,
            "institution_type": _identifier(institution_type, "institution_type"),
            "mechanism_refs": refs,
            "trajectory": trajectory,
            "causal_trace": causal_trace,
            "counterfactual_parent_id": (
                _identifier(counterfactual_parent_id, "counterfactual_parent_id")
                if counterfactual_parent_id else None
            ),
            "failure_classification": (
                _identifier(failure_classification, "failure_classification")
                if failure_classification else None
            ),
            "evidence_grade": self._evidence_grade(evidence_grade),
            "protected": bool(protected),
            "provenance": provenance,
            "created_by": _identifier(created_by, "created_by"),
            "created_at": at,
            "authoritative": False,
            "training_eligible": False,
            "overlap_checked": False,
            "requires_review": True,
            "binding_authority": False,
        }
        digest = sha256_json(record)
        with self._connection() as connection:
            for ref in refs:
                if not self._mechanism_exists(
                    connection, tenant_id, ref["mechanism_id"], ref["version"]
                ):
                    raise ActionNetPlatformError(
                        f"unknown mechanism reference: {ref['mechanism_id']}@{ref['version']}"
                    )
            if record["counterfactual_parent_id"] and connection.execute(
                """SELECT 1 FROM actionnet_experiences
                   WHERE tenant_id = ? AND experience_id = ?""",
                (tenant_id, record["counterfactual_parent_id"]),
            ).fetchone() is None:
                raise ActionNetPlatformError("counterfactual parent does not exist")
            try:
                connection.execute(
                    """INSERT INTO actionnet_experiences
                       (tenant_id, experience_id, source_type, institution_type,
                        mechanism_refs_json, trajectory_json, causal_trace_json,
                        counterfactual_parent_id, failure_classification, evidence_grade,
                        protected, provenance_json, created_by, created_at, content_sha256)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        tenant_id, record["experience_id"], source_type,
                        record["institution_type"], canonical_json(refs),
                        canonical_json(trajectory), canonical_json(causal_trace),
                        record["counterfactual_parent_id"], record["failure_classification"],
                        record["evidence_grade"], int(record["protected"]),
                        canonical_json(provenance), record["created_by"], at, digest,
                    ),
                )
            except sqlite3.IntegrityError as exc:
                raise ActionNetPlatformError("experience identity already exists") from exc
            self._audit(
                connection, tenant_id, "EXPERIENCE_RECORDED", record["experience_id"],
                {
                    "content_sha256": digest,
                    "protected": record["protected"],
                    "training_eligible": False,
                }, at,
            )
        return {**record, "content_sha256": digest}

    def _experience_row(
        self, connection: sqlite3.Connection, tenant_id: str, experience_id: str
    ) -> sqlite3.Row:
        row = connection.execute(
            """SELECT * FROM actionnet_experiences
               WHERE tenant_id = ? AND experience_id = ?""",
            (tenant_id, experience_id),
        ).fetchone()
        if row is None:
            raise ActionNetPlatformError("experience not found")
        return row

    def review_experience(
        self,
        tenant_id: str,
        review_id: str,
        experience_id: str,
        reviewer_id: str,
        reviewer_role: str,
        dimension: str,
        decision: str,
        rationale: str,
        *,
        created_at: str | None = None,
    ) -> dict[str, Any]:
        dimension = str(dimension).upper()
        decision = str(decision).upper()
        if dimension not in REVIEW_DIMENSIONS:
            raise ActionNetPlatformError(f"unsupported review dimension: {dimension}")
        if decision not in REVIEW_DECISIONS:
            raise ActionNetPlatformError(f"unsupported review decision: {decision}")
        reviewer_role = str(reviewer_role).upper()
        if reviewer_role not in REVIEW_ROLE_REQUIREMENTS[dimension]:
            raise ActionNetPlatformError(
                f"reviewer role {reviewer_role} cannot approve dimension {dimension}"
            )
        tenant_id = _identifier(tenant_id, "tenant_id")
        at = str(created_at or _now())
        with self._connection() as connection:
            experience = self._experience_row(connection, tenant_id, experience_id)
            review = {
                "schema_version": "actionnet-experience-review.v1",
                "tenant_id": tenant_id,
                "review_id": _identifier(review_id, "review_id"),
                "experience_id": _identifier(experience_id, "experience_id"),
                "reviewer_id": _identifier(reviewer_id, "reviewer_id"),
                "reviewer_role": reviewer_role,
                "dimension": dimension,
                "decision": decision,
                "rationale": _text(rationale, "rationale", minimum=10),
                "experience_sha256": experience["content_sha256"],
                "created_at": at,
                "binding_authority": False,
            }
            digest = sha256_json(review)
            try:
                connection.execute(
                    """INSERT INTO actionnet_experience_reviews
                       (tenant_id, review_id, experience_id, reviewer_id, reviewer_role,
                        dimension, decision, rationale, experience_sha256, created_at,
                        review_sha256) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        tenant_id, review["review_id"], review["experience_id"],
                        review["reviewer_id"], review["reviewer_role"], dimension,
                        decision, review["rationale"], review["experience_sha256"],
                        at, digest,
                    ),
                )
            except sqlite3.IntegrityError as exc:
                raise ActionNetPlatformError("review identity or reviewer dimension already exists") from exc
            self._audit(
                connection, tenant_id, "EXPERIENCE_REVIEWED", experience_id,
                {"review_sha256": digest, "dimension": dimension, "decision": decision}, at,
            )
        return {**review, "review_sha256": digest}

    def _governance_event(
        self,
        connection: sqlite3.Connection,
        tenant_id: str,
        experience_id: str,
        event_type: str,
        actor_id: str,
        details: dict[str, Any],
        created_at: str,
    ) -> dict[str, Any]:
        self._experience_row(connection, tenant_id, experience_id)
        event = {
            "tenant_id": tenant_id,
            "experience_id": experience_id,
            "event_type": event_type,
            "actor_id": actor_id,
            "details": details,
            "created_at": created_at,
        }
        digest = sha256_json(event)
        connection.execute(
            """INSERT INTO actionnet_governance_events
               (tenant_id, experience_id, event_type, actor_id, details_json,
                created_at, event_sha256) VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                tenant_id, experience_id, event_type, actor_id,
                canonical_json(details), created_at, digest,
            ),
        )
        self._audit(
            connection, tenant_id, event_type, experience_id,
            {"event_sha256": digest, **details}, created_at,
        )
        return {**event, "event_sha256": digest, "binding_authority": False}

    def record_overlap_check(
        self,
        tenant_id: str,
        experience_id: str,
        passed: bool,
        report: dict[str, Any],
        *,
        actor_id: str,
        created_at: str | None = None,
    ) -> dict[str, Any]:
        tenant_id = _identifier(tenant_id, "tenant_id")
        experience_id = _identifier(experience_id, "experience_id")
        report = _json_object(report, "overlap report")
        at = str(created_at or _now())
        event_type = "OVERLAP_CHECK_PASSED" if passed else "OVERLAP_CHECK_FAILED"
        with self._connection() as connection:
            return self._governance_event(
                connection, tenant_id, experience_id, event_type,
                _identifier(actor_id, "actor_id"),
                {"report_sha256": sha256_json(report), "report": report}, at,
            )

    def _reviews(self, connection: sqlite3.Connection, tenant_id: str, experience_id: str) -> list[sqlite3.Row]:
        return connection.execute(
            """SELECT * FROM actionnet_experience_reviews
               WHERE tenant_id = ? AND experience_id = ? ORDER BY created_at, review_id""",
            (tenant_id, experience_id),
        ).fetchall()

    def _events(self, connection: sqlite3.Connection, tenant_id: str, experience_id: str) -> list[sqlite3.Row]:
        return connection.execute(
            """SELECT * FROM actionnet_governance_events
               WHERE tenant_id = ? AND experience_id = ? ORDER BY sequence""",
            (tenant_id, experience_id),
        ).fetchall()

    def experience_state(self, tenant_id: str, experience_id: str) -> dict[str, Any]:
        with self._connection() as connection:
            row = self._experience_row(connection, tenant_id, experience_id)
            reviews = self._reviews(connection, tenant_id, experience_id)
            events = self._events(connection, tenant_id, experience_id)
        overlap_checked = any(event["event_type"] == "OVERLAP_CHECK_PASSED" for event in events)
        overlap_failed_after_pass = False
        latest_overlap = next(
            (event["event_type"] for event in reversed(events) if event["event_type"].startswith("OVERLAP_CHECK_")),
            None,
        )
        if latest_overlap == "OVERLAP_CHECK_FAILED":
            overlap_failed_after_pass = True
        eligible = any(event["event_type"] == "TRAINING_ELIGIBLE" for event in events)
        quarantined = any(event["event_type"] == "QUARANTINED" for event in events)
        result = dict(row)
        for key in ("mechanism_refs_json", "trajectory_json", "causal_trace_json", "provenance_json"):
            result[key.removesuffix("_json")] = json.loads(result.pop(key))
        result["protected"] = bool(result["protected"])
        result["authoritative"] = False
        result["training_eligible"] = eligible and not quarantined and not overlap_failed_after_pass
        result["overlap_checked"] = overlap_checked and not overlap_failed_after_pass
        result["requires_review"] = not result["training_eligible"]
        result["reviews"] = [dict(review) for review in reviews]
        result["governance_events"] = [
            {**dict(event), "details": json.loads(event["details_json"])} for event in events
        ]
        for event in result["governance_events"]:
            event.pop("details_json", None)
        result["binding_authority"] = False
        return result

    def approve_training_eligibility(
        self,
        tenant_id: str,
        experience_id: str,
        *,
        release_manager_id: str,
        rationale: str,
        created_at: str | None = None,
    ) -> dict[str, Any]:
        tenant_id = _identifier(tenant_id, "tenant_id")
        experience_id = _identifier(experience_id, "experience_id")
        at = str(created_at or _now())
        with self._connection() as connection:
            experience = self._experience_row(connection, tenant_id, experience_id)
            if bool(experience["protected"]):
                raise ActionNetPlatformError("protected experience cannot become training eligible")
            if experience["evidence_grade"] == "UNVERIFIED":
                raise ActionNetPlatformError("unverified experience cannot become training eligible")
            reviews = self._reviews(connection, tenant_id, experience_id)
            if any(review["decision"] == "REJECT" for review in reviews):
                raise ActionNetPlatformError("rejected experience cannot become training eligible")
            approved_dimensions = {
                review["dimension"] for review in reviews if review["decision"] == "APPROVE"
            }
            required = {"DOMAIN", "SAFETY", "LINEAGE", "TRAINING"}
            if experience["source_type"] == "REAL_GOVERNED_ABSTRACTION":
                required.add("PRIVACY")
            missing = sorted(required - approved_dimensions)
            if missing:
                raise ActionNetPlatformError(
                    "training eligibility missing approvals: " + ", ".join(missing)
                )
            domain_reviewers = {
                review["reviewer_id"] for review in reviews
                if review["dimension"] == "DOMAIN" and review["decision"] == "APPROVE"
            }
            safety_reviewers = {
                review["reviewer_id"] for review in reviews
                if review["dimension"] == "SAFETY" and review["decision"] == "APPROVE"
            }
            if domain_reviewers & safety_reviewers:
                raise ActionNetPlatformError(
                    "domain and safety approvals require distinct reviewers"
                )
            events = self._events(connection, tenant_id, experience_id)
            latest_overlap = next(
                (event["event_type"] for event in reversed(events) if event["event_type"].startswith("OVERLAP_CHECK_")),
                None,
            )
            if latest_overlap != "OVERLAP_CHECK_PASSED":
                raise ActionNetPlatformError("training eligibility requires a passing overlap check")
            if any(event["event_type"] == "QUARANTINED" for event in events):
                raise ActionNetPlatformError("quarantined experience cannot become training eligible")
            return self._governance_event(
                connection, tenant_id, experience_id, "TRAINING_ELIGIBLE",
                _identifier(release_manager_id, "release_manager_id"),
                {"rationale": _text(rationale, "rationale", minimum=10)}, at,
            )

    def quarantine_experience(
        self,
        tenant_id: str,
        experience_id: str,
        reason: str,
        *,
        actor_id: str,
        created_at: str | None = None,
    ) -> dict[str, Any]:
        with self._connection() as connection:
            return self._governance_event(
                connection, _identifier(tenant_id, "tenant_id"),
                _identifier(experience_id, "experience_id"), "QUARANTINED",
                _identifier(actor_id, "actor_id"),
                {"reason": _text(reason, "reason", minimum=10)},
                str(created_at or _now()),
            )

    def record_model_exposure(
        self,
        tenant_id: str,
        exposure_id: str,
        experience_id: str,
        model_id: str,
        purpose: str,
        *,
        created_by: str,
        dataset_release_id: str | None = None,
        created_at: str | None = None,
    ) -> dict[str, Any]:
        purpose = str(purpose).upper()
        if purpose not in EXPOSURE_PURPOSES:
            raise ActionNetPlatformError(f"unsupported exposure purpose: {purpose}")
        tenant_id = _identifier(tenant_id, "tenant_id")
        state = self.experience_state(tenant_id, experience_id)
        if state["protected"] and purpose != "PROTECTED_EVALUATION":
            raise ActionNetPlatformError("protected experience may only be used for protected evaluation")
        if purpose == "TRAIN" and not state["training_eligible"]:
            raise ActionNetPlatformError("training exposure requires training eligibility")
        at = str(created_at or _now())
        record = {
            "tenant_id": tenant_id,
            "exposure_id": _identifier(exposure_id, "exposure_id"),
            "experience_id": _identifier(experience_id, "experience_id"),
            "model_id": _identifier(model_id, "model_id"),
            "dataset_release_id": (
                _identifier(dataset_release_id, "dataset_release_id")
                if dataset_release_id else None
            ),
            "purpose": purpose,
            "created_by": _identifier(created_by, "created_by"),
            "created_at": at,
            "binding_authority": False,
        }
        digest = sha256_json(record)
        with self._connection() as connection:
            try:
                connection.execute(
                    """INSERT INTO actionnet_model_exposures
                       (tenant_id, exposure_id, experience_id, model_id,
                        dataset_release_id, purpose, created_by, created_at, record_sha256)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        tenant_id, record["exposure_id"], record["experience_id"],
                        record["model_id"], record["dataset_release_id"], purpose,
                        record["created_by"], at, digest,
                    ),
                )
            except sqlite3.IntegrityError as exc:
                raise ActionNetPlatformError("exposure identity or duplicate exposure already exists") from exc
            self._audit(
                connection, tenant_id, "MODEL_EXPOSURE_RECORDED", record["experience_id"],
                {"record_sha256": digest, "model_id": record["model_id"], "purpose": purpose}, at,
            )
        return {**record, "record_sha256": digest}

    def coverage_report(
        self,
        tenant_id: str,
        *,
        minimum_experiences: int = 3,
        minimum_domains: int = 2,
    ) -> dict[str, Any]:
        tenant_id = _identifier(tenant_id, "tenant_id")
        if minimum_experiences < 1 or minimum_domains < 1:
            raise ActionNetPlatformError("coverage minimums must be positive")
        with self._connection() as connection:
            mechanisms = connection.execute(
                """SELECT * FROM actionnet_mechanisms
                   WHERE tenant_id = ? ORDER BY mechanism_id, version""",
                (tenant_id,),
            ).fetchall()
            experiences = connection.execute(
                "SELECT * FROM actionnet_experiences WHERE tenant_id = ?",
                (tenant_id,),
            ).fetchall()
        rows = []
        for mechanism in mechanisms:
            relevant = [
                experience for experience in experiences
                if {"mechanism_id": mechanism["mechanism_id"], "version": mechanism["version"]}
                in json.loads(experience["mechanism_refs_json"])
            ]
            domains = sorted({experience["institution_type"] for experience in relevant})
            source_types = sorted({experience["source_type"] for experience in relevant})
            evidence_grades = sorted({experience["evidence_grade"] for experience in relevant})
            counterfactual_count = sum(bool(experience["counterfactual_parent_id"]) for experience in relevant)
            failure_count = sum(bool(experience["failure_classification"]) for experience in relevant)
            protected_count = sum(bool(experience["protected"]) for experience in relevant)
            components = {
                "experience_depth": min(1.0, len(relevant) / minimum_experiences),
                "domain_breadth": min(1.0, len(domains) / minimum_domains),
                "failure_coverage": 1.0 if failure_count else 0.0,
                "counterfactual_coverage": 1.0 if counterfactual_count else 0.0,
                "protected_coverage": 1.0 if protected_count else 0.0,
            }
            score = (
                components["experience_depth"] * 0.35
                + components["domain_breadth"] * 0.20
                + components["failure_coverage"] * 0.15
                + components["counterfactual_coverage"] * 0.15
                + components["protected_coverage"] * 0.15
            )
            rows.append(
                {
                    "mechanism_id": mechanism["mechanism_id"],
                    "version": mechanism["version"],
                    "experience_count": len(relevant),
                    "domains": domains,
                    "source_types": source_types,
                    "evidence_grades": evidence_grades,
                    "failure_count": failure_count,
                    "counterfactual_count": counterfactual_count,
                    "protected_count": protected_count,
                    "registered_coverage_score": round(score, 6),
                    "components": components,
                }
            )
        overall = sum(row["registered_coverage_score"] for row in rows) / len(rows) if rows else 0.0
        return {
            "schema_version": "actionnet-coverage-report.v1",
            "tenant_id": tenant_id,
            "registered_universe": {
                "mechanism_versions": len(rows),
                "minimum_experiences": minimum_experiences,
                "minimum_domains": minimum_domains,
                "weights": {
                    "experience_depth": 0.35,
                    "domain_breadth": 0.20,
                    "failure_coverage": 0.15,
                    "counterfactual_coverage": 0.15,
                    "protected_coverage": 0.15,
                },
            },
            "mechanisms": rows,
            "registered_coverage_score": round(overall, 6),
            "claim_boundary": "Coverage is limited to the registered product matrix, not all institutions.",
            "binding_authority": False,
        }

    def freeze_coverage_snapshot(
        self,
        tenant_id: str,
        snapshot_id: str,
        *,
        created_by: str,
        minimum_experiences: int = 3,
        minimum_domains: int = 2,
        created_at: str | None = None,
    ) -> dict[str, Any]:
        report = self.coverage_report(
            tenant_id,
            minimum_experiences=minimum_experiences,
            minimum_domains=minimum_domains,
        )
        at = str(created_at or _now())
        digest = sha256_json(report)
        with self._connection() as connection:
            connection.execute(
                """INSERT INTO actionnet_coverage_snapshots
                   (tenant_id, snapshot_id, report_json, registered_universe_json,
                    created_by, created_at, report_sha256) VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (
                    tenant_id, _identifier(snapshot_id, "snapshot_id"),
                    canonical_json(report), canonical_json(report["registered_universe"]),
                    _identifier(created_by, "created_by"), at, digest,
                ),
            )
            self._audit(
                connection, tenant_id, "COVERAGE_SNAPSHOT_FROZEN", snapshot_id,
                {"report_sha256": digest}, at,
            )
        return {"snapshot_id": snapshot_id, "report": report, "report_sha256": digest}

    def recommend_acquisition(
        self,
        tenant_id: str,
        recommendation_id: str,
        *,
        created_by: str,
        minimum_experiences: int = 3,
        minimum_domains: int = 2,
        created_at: str | None = None,
    ) -> dict[str, Any]:
        report = self.coverage_report(
            tenant_id,
            minimum_experiences=minimum_experiences,
            minimum_domains=minimum_domains,
        )
        ranked = sorted(
            report["mechanisms"],
            key=lambda row: (row["registered_coverage_score"], row["mechanism_id"], row["version"]),
        )
        if not ranked:
            raise ActionNetPlatformError("cannot recommend acquisition without mechanisms")
        frontier = ranked[: min(5, len(ranked))]
        gaps: set[str] = set()
        for row in frontier:
            if row["experience_count"] < minimum_experiences:
                gaps.add("EXPERIENCE_DEPTH")
            if len(row["domains"]) < minimum_domains:
                gaps.add("DOMAIN_BREADTH")
            if row["failure_count"] == 0:
                gaps.add("FAILURE_COVERAGE")
            if row["counterfactual_count"] == 0:
                gaps.add("COUNTERFACTUAL_COVERAGE")
            if row["protected_count"] == 0:
                gaps.add("PROTECTED_COVERAGE")
        target_ids = [f"{row['mechanism_id']}@{row['version']}" for row in frontier]
        average_gap = 1.0 - sum(row["registered_coverage_score"] for row in frontier) / len(frontier)
        at = str(created_at or _now())
        record = {
            "schema_version": "actionnet-acquisition-recommendation.v1",
            "tenant_id": tenant_id,
            "recommendation_id": _identifier(recommendation_id, "recommendation_id"),
            "target_mechanism_ids": target_ids,
            "gap_dimensions": sorted(gaps),
            "rationale": "Acquire governed experiences for the lowest-scoring registered mechanism coverage cells.",
            "priority": round(average_gap, 6),
            "expected_information_gain": round(min(1.0, average_gap), 6),
            "evidence": {"coverage_report_sha256": sha256_json(report)},
            "created_by": _identifier(created_by, "created_by"),
            "created_at": at,
            "authoritative": False,
            "training_eligible": False,
            "binding_authority": False,
        }
        digest = sha256_json(record)
        with self._connection() as connection:
            connection.execute(
                """INSERT INTO actionnet_acquisition_recommendations
                   (tenant_id, recommendation_id, target_mechanism_ids_json,
                    gap_dimensions_json, rationale, priority,
                    expected_information_gain, evidence_json, created_by,
                    created_at, record_sha256) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    tenant_id, record["recommendation_id"], canonical_json(target_ids),
                    canonical_json(record["gap_dimensions"]), record["rationale"],
                    record["priority"], record["expected_information_gain"],
                    canonical_json(record["evidence"]), record["created_by"], at, digest,
                ),
            )
            self._audit(
                connection, tenant_id, "ACQUISITION_RECOMMENDED",
                record["recommendation_id"], {"record_sha256": digest}, at,
            )
        return {**record, "record_sha256": digest}

    def record_intervention_candidate(
        self,
        tenant_id: str,
        intervention_id: str,
        scope_id: str,
        source_experience_ids: Iterable[str],
        action: dict[str, Any],
        objectives: dict[str, Any],
        constraints: dict[str, Any],
        predicted_outcomes: dict[str, Any],
        verification: dict[str, Any],
        confidence: float,
        *,
        created_by: str,
        created_at: str | None = None,
    ) -> dict[str, Any]:
        tenant_id = _identifier(tenant_id, "tenant_id")
        action = _json_object(action, "action")
        objectives = _json_object(objectives, "objectives")
        constraints = _json_object(constraints, "constraints")
        predicted_outcomes = _json_object(predicted_outcomes, "predicted_outcomes")
        verification = _json_object(verification, "verification")
        _forbid_authority(action, "action")
        source_ids = _string_list(source_experience_ids, "source_experience_id")
        if not source_ids:
            raise ActionNetPlatformError("intervention requires source experiences")
        at = str(created_at or _now())
        record = {
            "schema_version": "actionnet-intervention-candidate.v1",
            "tenant_id": tenant_id,
            "intervention_id": _identifier(intervention_id, "intervention_id"),
            "scope_id": _identifier(scope_id, "scope_id"),
            "source_experience_ids": source_ids,
            "action": action,
            "objectives": objectives,
            "constraints": constraints,
            "predicted_outcomes": predicted_outcomes,
            "verification": verification,
            "confidence": _score(confidence, "confidence"),
            "created_by": _identifier(created_by, "created_by"),
            "created_at": at,
            "authoritative": False,
            "training_eligible": False,
            "requires_expert_review": True,
            "requires_kernel_authorization": True,
            "binding_authority": False,
        }
        digest = sha256_json(record)
        with self._connection() as connection:
            for source_id in source_ids:
                self._experience_row(connection, tenant_id, source_id)
            connection.execute(
                """INSERT INTO actionnet_intervention_candidates
                   (tenant_id, intervention_id, scope_id, source_experience_ids_json,
                    action_json, objectives_json, constraints_json,
                    predicted_outcomes_json, verification_json, confidence,
                    created_by, created_at, record_sha256)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    tenant_id, record["intervention_id"], record["scope_id"],
                    canonical_json(source_ids), canonical_json(action),
                    canonical_json(objectives), canonical_json(constraints),
                    canonical_json(predicted_outcomes), canonical_json(verification),
                    record["confidence"], record["created_by"], at, digest,
                ),
            )
            self._audit(
                connection, tenant_id, "INTERVENTION_CANDIDATE_RECORDED",
                record["intervention_id"], {"record_sha256": digest}, at,
            )
        return {**record, "record_sha256": digest}

    def create_training_release(
        self,
        tenant_id: str,
        release_id: str,
        experience_ids: Iterable[str],
        model_target: str,
        *,
        release_manager_id: str,
        created_at: str | None = None,
    ) -> dict[str, Any]:
        tenant_id = _identifier(tenant_id, "tenant_id")
        ids = _string_list(experience_ids, "experience_id")
        if not ids:
            raise ActionNetPlatformError("training release requires experiences")
        hashes: dict[str, str] = {}
        for experience_id in ids:
            state = self.experience_state(tenant_id, experience_id)
            if state["protected"]:
                raise ActionNetPlatformError("training release cannot include protected experience")
            if not state["training_eligible"]:
                raise ActionNetPlatformError(
                    f"experience is not training eligible: {experience_id}"
                )
            hashes[experience_id] = state["content_sha256"]
        at = str(created_at or _now())
        record = {
            "schema_version": "actionnet-training-release.v1",
            "tenant_id": tenant_id,
            "release_id": _identifier(release_id, "release_id"),
            "experience_ids": ids,
            "experience_hashes": hashes,
            "model_target": _identifier(model_target, "model_target"),
            "release_manager_id": _identifier(release_manager_id, "release_manager_id"),
            "created_at": at,
            "binding_authority": False,
        }
        digest = sha256_json(record)
        with self._connection() as connection:
            connection.execute(
                """INSERT INTO actionnet_training_releases
                   (tenant_id, release_id, experience_ids_json, experience_hashes_json,
                    model_target, release_manager_id, created_at, release_sha256)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    tenant_id, record["release_id"], canonical_json(ids),
                    canonical_json(hashes), record["model_target"],
                    record["release_manager_id"], at, digest,
                ),
            )
            self._audit(
                connection, tenant_id, "TRAINING_RELEASE_CREATED", record["release_id"],
                {"release_sha256": digest, "experience_count": len(ids)}, at,
            )
        return {**record, "release_sha256": digest}

    def record_composition_run(
        self,
        tenant_id: str,
        run: dict[str, Any],
        *,
        protected: bool,
        created_by: str,
        created_at: str | None = None,
    ) -> dict[str, Any]:
        tenant_id = _identifier(tenant_id, "tenant_id")
        run = _json_object(run, "composition run")
        _forbid_authority(run, "composition_run")
        if run.get("schema_version") != "actionnet-composition-run.v1":
            raise ActionNetPlatformError("unsupported composition run schema")
        if run.get("verification", {}).get("deterministic_replay") is not True:
            raise ActionNetPlatformError("composition run must pass deterministic replay")
        ir_ref = run.get("institution_ir", {})
        run_id = _identifier(run.get("run_id"), "run_id")
        institution_id = _identifier(ir_ref.get("institution_id"), "institution_id")
        institution_version = _identifier(ir_ref.get("version"), "institution_version")
        stored_ir = self.institutional_ir(tenant_id, institution_id, institution_version)
        if stored_ir["institutional_ir"]["ir_sha256"] != ir_ref.get("ir_sha256"):
            raise ActionNetPlatformError("composition run Institutional IR hash mismatch")
        for ref in run.get("mechanism_refs", []):
            self.mechanism(tenant_id, str(ref["mechanism_id"]), str(ref["version"]))
        for edge_id in run.get("edge_refs", []):
            self.composition_edge(tenant_id, str(edge_id))
        at = str(created_at or _now())
        record = {
            "schema_version": "actionnet-composition-run-record.v1",
            "tenant_id": tenant_id,
            "run_id": run_id,
            "institution_id": institution_id,
            "institution_version": institution_version,
            "run": run,
            "protected": bool(protected),
            "created_by": _identifier(created_by, "created_by"),
            "created_at": at,
            "binding_authority": False,
        }
        digest = sha256_json(record)
        with self._connection() as connection:
            try:
                connection.execute(
                    """INSERT INTO actionnet_composition_runs
                       (tenant_id, run_id, institution_id, institution_version, run_json,
                        protected, created_by, created_at, record_sha256)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        tenant_id, run_id, institution_id, institution_version,
                        canonical_json(run), int(bool(protected)), record["created_by"], at, digest,
                    ),
                )
            except sqlite3.IntegrityError as exc:
                raise ActionNetPlatformError("composition run already exists") from exc
            self._audit(
                connection, tenant_id, "COMPOSITION_EXECUTED", run_id,
                {"record_sha256": digest, "protected": bool(protected)}, at,
            )
        return {**record, "record_sha256": digest}

    def composition_run(self, tenant_id: str, run_id: str) -> dict[str, Any]:
        with self._connection() as connection:
            row = connection.execute(
                """SELECT * FROM actionnet_composition_runs
                   WHERE tenant_id = ? AND run_id = ?""",
                (tenant_id, run_id),
            ).fetchone()
        if row is None:
            raise ActionNetPlatformError("composition run not found")
        return {
            "schema_version": "actionnet-composition-run-record.v1",
            "tenant_id": row["tenant_id"],
            "run_id": row["run_id"],
            "institution_id": row["institution_id"],
            "institution_version": row["institution_version"],
            "run": json.loads(row["run_json"]),
            "protected": bool(row["protected"]),
            "created_by": row["created_by"],
            "created_at": row["created_at"],
            "record_sha256": row["record_sha256"],
            "binding_authority": False,
        }

    def record_counterfactual_batch(
        self,
        tenant_id: str,
        batch: dict[str, Any],
        child_experience_ids: Iterable[str],
        *,
        protected: bool,
        created_by: str,
        created_at: str | None = None,
    ) -> dict[str, Any]:
        tenant_id = _identifier(tenant_id, "tenant_id")
        batch = _json_object(batch, "counterfactual batch")
        _forbid_authority(batch, "counterfactual_batch")
        if batch.get("schema_version") != "actionnet-counterfactual-batch.v1":
            raise ActionNetPlatformError("unsupported counterfactual batch schema")
        if batch.get("all_branches_replay_verified") is not True:
            raise ActionNetPlatformError("counterfactual batch requires replay-verified branches")
        batch_id = _identifier(batch.get("batch_id"), "batch_id")
        parent_id = _identifier(batch.get("parent_experience_id"), "parent_experience_id")
        parent = self.experience_state(tenant_id, parent_id)
        if bool(parent["protected"]) != bool(protected):
            raise ActionNetPlatformError("counterfactual protection must match its parent")
        children = _string_list(child_experience_ids, "child_experience_id")
        expected_count = len(batch.get("branches", []))
        if not children or len(children) != expected_count:
            raise ActionNetPlatformError("counterfactual child experiences must match branch count")
        for child_id in children:
            child = self.experience_state(tenant_id, child_id)
            if child["counterfactual_parent_id"] != parent_id:
                raise ActionNetPlatformError("counterfactual child has incorrect parent")
            if bool(child["protected"]) != bool(protected):
                raise ActionNetPlatformError("counterfactual child protection mismatch")
        at = str(created_at or _now())
        record = {
            "schema_version": "actionnet-counterfactual-batch-record.v1",
            "tenant_id": tenant_id,
            "batch_id": batch_id,
            "parent_experience_id": parent_id,
            "batch": batch,
            "child_experience_ids": children,
            "protected": bool(protected),
            "created_by": _identifier(created_by, "created_by"),
            "created_at": at,
            "binding_authority": False,
        }
        digest = sha256_json(record)
        with self._connection() as connection:
            try:
                connection.execute(
                    """INSERT INTO actionnet_counterfactual_batches
                       (tenant_id, batch_id, parent_experience_id, batch_json,
                        child_experience_ids_json, protected, created_by, created_at, record_sha256)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        tenant_id, batch_id, parent_id, canonical_json(batch),
                        canonical_json(children), int(bool(protected)), record["created_by"], at, digest,
                    ),
                )
            except sqlite3.IntegrityError as exc:
                raise ActionNetPlatformError("counterfactual batch already exists") from exc
            self._audit(
                connection, tenant_id, "COUNTERFACTUAL_BATCH_RECORDED", batch_id,
                {"record_sha256": digest, "branch_count": len(children), "protected": bool(protected)}, at,
            )
        return {**record, "record_sha256": digest}

    def record_behavior_scenario(
        self,
        tenant_id: str,
        scenario_id: str,
        institution_id: str,
        institution_version: str,
        scenario: dict[str, Any],
        *,
        protected: bool,
        created_by: str,
        created_at: str | None = None,
    ) -> dict[str, Any]:
        tenant_id = _identifier(tenant_id, "tenant_id")
        scenario = _json_object(scenario, "behavior scenario")
        _forbid_authority(scenario, "behavior_scenario")
        if scenario.get("model_status") != "ASSUMPTION_DRIVEN_SCENARIO_NOT_HUMAN_GROUND_TRUTH":
            raise ActionNetPlatformError("behavior scenario must preserve its assumption-driven boundary")
        ir = self.institutional_ir(tenant_id, institution_id, institution_version)
        if scenario.get("institution_ir_sha256") != ir["institutional_ir"]["ir_sha256"]:
            raise ActionNetPlatformError("behavior scenario Institutional IR hash mismatch")
        at = str(created_at or _now())
        record = {
            "schema_version": "actionnet-behavior-scenario-record.v1",
            "tenant_id": tenant_id,
            "scenario_id": _identifier(scenario_id, "scenario_id"),
            "institution_id": _identifier(institution_id, "institution_id"),
            "institution_version": _identifier(institution_version, "institution_version"),
            "scenario": scenario,
            "protected": bool(protected),
            "created_by": _identifier(created_by, "created_by"),
            "created_at": at,
            "authoritative": False,
            "binding_authority": False,
        }
        digest = sha256_json(record)
        with self._connection() as connection:
            try:
                connection.execute(
                    """INSERT INTO actionnet_behavior_scenarios
                       (tenant_id, scenario_id, institution_id, institution_version,
                        scenario_json, protected, created_by, created_at, record_sha256)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        tenant_id, record["scenario_id"], record["institution_id"],
                        record["institution_version"], canonical_json(scenario),
                        int(bool(protected)), record["created_by"], at, digest,
                    ),
                )
            except sqlite3.IntegrityError as exc:
                raise ActionNetPlatformError("behavior scenario already exists") from exc
            self._audit(
                connection, tenant_id, "BEHAVIOR_SCENARIO_RECORDED", record["scenario_id"],
                {"record_sha256": digest, "protected": bool(protected)}, at,
            )
        return {**record, "record_sha256": digest}

    def record_governed_intake(
        self,
        tenant_id: str,
        abstraction: dict[str, Any],
        experience_id: str,
        *,
        created_by: str,
        created_at: str | None = None,
    ) -> dict[str, Any]:
        tenant_id = _identifier(tenant_id, "tenant_id")
        normalized = GovernedAbstractionValidator().normalize(abstraction)
        ir_ref = normalized["institution_ir_ref"]
        self.institutional_ir(tenant_id, ir_ref["institution_id"], ir_ref["version"])
        experience = self.experience_state(tenant_id, experience_id)
        if experience["source_type"] != "REAL_GOVERNED_ABSTRACTION":
            raise ActionNetPlatformError("governed intake must create a real governed abstraction experience")
        if experience["training_eligible"]:
            raise ActionNetPlatformError("new governed intake experience cannot already be training eligible")
        at = str(created_at or _now())
        record = {
            "schema_version": "actionnet-governed-intake-record.v1",
            "tenant_id": tenant_id,
            "intake_id": _identifier(normalized["intake_id"], "intake_id"),
            "institution_id": ir_ref["institution_id"],
            "institution_version": ir_ref["version"],
            "experience_id": _identifier(experience_id, "experience_id"),
            "abstraction": normalized,
            "created_by": _identifier(created_by, "created_by"),
            "created_at": at,
            "raw_payload_stored": False,
            "training_eligible": False,
            "binding_authority": False,
        }
        digest = sha256_json(record)
        with self._connection() as connection:
            try:
                connection.execute(
                    """INSERT INTO actionnet_governed_intakes
                       (tenant_id, intake_id, institution_id, institution_version,
                        experience_id, abstraction_json, created_by, created_at, record_sha256)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        tenant_id, record["intake_id"], record["institution_id"],
                        record["institution_version"], record["experience_id"],
                        canonical_json(normalized), record["created_by"], at, digest,
                    ),
                )
            except sqlite3.IntegrityError as exc:
                raise ActionNetPlatformError("governed abstraction intake already exists") from exc
            self._audit(
                connection, tenant_id, "GOVERNED_ABSTRACTION_INGESTED", record["intake_id"],
                {"record_sha256": digest, "experience_id": record["experience_id"], "raw_payload_stored": False},
                at,
            )
        return {**record, "record_sha256": digest}

    def list_institutional_ir(self, tenant_id: str, *, include_protected: bool = False) -> list[dict[str, Any]]:
        with self._connection() as connection:
            rows = connection.execute(
                """SELECT institution_id, version FROM actionnet_institutional_ir
                   WHERE tenant_id = ? AND (? = 1 OR protected = 0)
                   ORDER BY institution_id, version""",
                (tenant_id, int(include_protected)),
            ).fetchall()
        return [self.institutional_ir(tenant_id, row["institution_id"], row["version"]) for row in rows]

    def list_mechanisms(self, tenant_id: str) -> list[dict[str, Any]]:
        with self._connection() as connection:
            rows = connection.execute(
                """SELECT * FROM actionnet_mechanisms
                   WHERE tenant_id = ? ORDER BY mechanism_id, version""",
                (tenant_id,),
            ).fetchall()
        result = []
        for row in rows:
            item = dict(row)
            item["specification"] = json.loads(item.pop("specification_json"))
            item["domains"] = json.loads(item.pop("domains_json"))
            item["source_lineage"] = json.loads(item.pop("source_lineage_json"))
            item["binding_authority"] = False
            result.append(item)
        return result

    def list_experiences(self, tenant_id: str, *, include_protected: bool = False) -> list[dict[str, Any]]:
        with self._connection() as connection:
            rows = connection.execute(
                """SELECT experience_id FROM actionnet_experiences
                   WHERE tenant_id = ? AND (? = 1 OR protected = 0)
                   ORDER BY created_at, experience_id""",
                (tenant_id, int(include_protected)),
            ).fetchall()
        return [self.experience_state(tenant_id, row["experience_id"]) for row in rows]

    def audit_events(self, tenant_id: str) -> list[dict[str, Any]]:
        with self._connection() as connection:
            rows = connection.execute(
                """SELECT * FROM actionnet_product_audit
                   WHERE tenant_id = ? ORDER BY sequence""",
                (tenant_id,),
            ).fetchall()
        return [{**dict(row), "payload": json.loads(row["payload_json"])} for row in rows]

    def verify_audit_chain(self, tenant_id: str) -> bool:
        previous = "GENESIS"
        for row in self.audit_events(tenant_id):
            record = {
                "tenant_id": row["tenant_id"],
                "event_type": row["event_type"],
                "entity_id": row["entity_id"],
                "payload": row["payload"],
                "previous_hash": row["previous_hash"],
                "created_at": row["created_at"],
            }
            if row["previous_hash"] != previous or sha256_json(record) != row["event_hash"]:
                return False
            previous = row["event_hash"]
        return True

    def counts(self) -> dict[str, int]:
        tables = {
            "institutional_ir_versions": "actionnet_institutional_ir",
            "mechanisms": "actionnet_mechanisms",
            "composition_edges": "actionnet_composition_edges",
            "world_blueprints": "actionnet_world_blueprints",
            "experiences": "actionnet_experiences",
            "protected_experiences": "actionnet_experiences WHERE protected = 1",
            "reviews": "actionnet_experience_reviews",
            "acquisition_recommendations": "actionnet_acquisition_recommendations",
            "intervention_candidates": "actionnet_intervention_candidates",
            "training_releases": "actionnet_training_releases",
            "composition_runs": "actionnet_composition_runs",
            "counterfactual_batches": "actionnet_counterfactual_batches",
            "behavior_scenarios": "actionnet_behavior_scenarios",
            "governed_intakes": "actionnet_governed_intakes",
        }
        with self._connection() as connection:
            return {
                key: connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
                for key, table in tables.items()
            }