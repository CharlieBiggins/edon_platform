"""Governed local-to-global ActionNet learning and C1 version custody."""

from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Iterable

from edon.common.hashing import canonical_json, sha256_json

from .product import ActionNetPlatformStore


class LearningNetworkError(RuntimeError):
    """Raised when an experience or model crosses an unauthorized boundary."""


RIGHTS_BASES = {
    "CUSTOMER_CONSENT",
    "CONTRACTUAL_DERIVED_USE",
    "PUBLIC_SOURCE",
    "SYNTHETIC",
    "EXPERT_LICENSED",
    "FEDERATED_CONTRIBUTION",
}
PERMITTED_USES = {"TRAIN", "DEVELOPMENT", "DIAGNOSTIC"}
EVALUATION_STATES = {"PASS", "FAIL", "HOLD", "NOT_TESTED", "NOT_APPLICABLE"}
C1_DISPOSITIONS = {
    "SHADOW_ELIGIBLE",
    "DEPLOYMENT_ELIGIBLE",
    "ROLLBACK_REQUIRED",
    "REVOKED",
    "ARCHIVED",
}

_FORBIDDEN_GLOBAL_FIELDS = {
    "tenant_id",
    "experience_id",
    "patient_name",
    "person_name",
    "email",
    "phone",
    "address",
    "ssn",
    "medical_record_number",
    "raw_payload",
    "raw_text",
    "secret",
    "password",
    "api_key",
    "authorization_ref",
    "authorization_ref_sha256",
    "execution_token",
    "kernel_token",
    "commit_token",
    "binding_authority",
}


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _identifier(value: Any, label: str) -> str:
    normalized = str(value or "").strip()
    if not normalized or len(normalized) > 240:
        raise LearningNetworkError(f"{label} must contain between 1 and 240 characters")
    return normalized


def _text(value: Any, label: str, *, minimum: int = 10, maximum: int = 10_000) -> str:
    normalized = str(value or "").strip()
    if len(normalized) < minimum or len(normalized) > maximum:
        raise LearningNetworkError(
            f"{label} must contain between {minimum} and {maximum} characters"
        )
    return normalized


def _sha256(value: Any, label: str) -> str:
    normalized = str(value or "").strip()
    if not normalized.startswith("sha256:") or len(normalized) != 71:
        raise LearningNetworkError(f"{label} must be a prefixed SHA-256 digest")
    try:
        int(normalized.split(":", 1)[1], 16)
    except ValueError as exc:
        raise LearningNetworkError(f"{label} must be a prefixed SHA-256 digest") from exc
    return normalized


def _timestamp(value: Any, label: str) -> str:
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError as exc:
        raise LearningNetworkError(f"{label} must be an ISO-8601 timestamp") from exc
    if parsed.tzinfo is None:
        raise LearningNetworkError(f"{label} must include a timezone")
    return parsed.astimezone(UTC).isoformat()


def _json_object(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise LearningNetworkError(f"{label} must be a JSON object")
    try:
        serialized = json.dumps(value, allow_nan=False)
    except (TypeError, ValueError) as exc:
        raise LearningNetworkError(f"{label} must contain finite JSON values") from exc
    return json.loads(serialized)


def _string_set(values: Iterable[Any], label: str) -> list[str]:
    return sorted({_identifier(value, label) for value in values})


def _forbidden_paths(value: Any, prefix: str = "normalized_experience") -> list[str]:
    paths: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            path = f"{prefix}.{key}"
            if str(key).lower() in _FORBIDDEN_GLOBAL_FIELDS:
                paths.append(path)
            paths.extend(_forbidden_paths(child, path))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            paths.extend(_forbidden_paths(child, f"{prefix}[{index}]"))
    return paths


class GovernedLearningNetwork:
    """Promote governed local experience into global releases and frozen C1 versions.

    Local ActionNet remains the authority for tenant experience eligibility.
    Global records contain only normalized abstractions and source commitments;
    they never contain tenant identities or raw local payloads.
    """

    def __init__(self, path: Path | str, local_actionnet: ActionNetPlatformStore):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.local_actionnet = local_actionnet
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
                CREATE TABLE IF NOT EXISTS actionnet_local_exports (
                    tenant_id TEXT NOT NULL,
                    request_id TEXT NOT NULL,
                    experience_id TEXT NOT NULL,
                    experience_sha256 TEXT NOT NULL,
                    global_record_id TEXT NOT NULL UNIQUE,
                    normalized_experience_sha256 TEXT NOT NULL,
                    request_sha256 TEXT NOT NULL UNIQUE,
                    requested_by TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    PRIMARY KEY (tenant_id, request_id)
                );
                CREATE TABLE IF NOT EXISTS actionnet_global_records (
                    global_record_id TEXT PRIMARY KEY,
                    source_commitment_sha256 TEXT NOT NULL UNIQUE,
                    normalized_experience_json TEXT NOT NULL,
                    normalized_experience_sha256 TEXT NOT NULL,
                    evidence_grade TEXT NOT NULL,
                    rights_basis TEXT NOT NULL,
                    rights_ref_sha256 TEXT NOT NULL,
                    privacy_review_sha256 TEXT NOT NULL,
                    source_review_sha256 TEXT NOT NULL,
                    permitted_uses_json TEXT NOT NULL,
                    approved_by TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    record_sha256 TEXT NOT NULL UNIQUE
                );
                CREATE TABLE IF NOT EXISTS actionnet_global_events (
                    sequence INTEGER PRIMARY KEY AUTOINCREMENT,
                    global_record_id TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    actor_id TEXT NOT NULL,
                    reason TEXT NOT NULL,
                    evidence_ref_sha256 TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    event_sha256 TEXT NOT NULL UNIQUE,
                    FOREIGN KEY (global_record_id) REFERENCES actionnet_global_records(global_record_id)
                );
                CREATE TABLE IF NOT EXISTS actionnet_global_training_releases (
                    release_id TEXT PRIMARY KEY,
                    global_record_ids_json TEXT NOT NULL,
                    global_record_hashes_json TEXT NOT NULL,
                    model_target TEXT NOT NULL,
                    protected_evaluation_reservation_sha256 TEXT NOT NULL,
                    dataset_overlap_report_sha256 TEXT NOT NULL,
                    release_manager_id TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    release_sha256 TEXT NOT NULL UNIQUE
                );
                CREATE TABLE IF NOT EXISTS c1_model_versions (
                    model_id TEXT PRIMARY KEY,
                    predecessor_model_id TEXT,
                    base_model TEXT NOT NULL,
                    model_lineage TEXT NOT NULL,
                    training_release_id TEXT NOT NULL,
                    training_release_sha256 TEXT NOT NULL,
                    artifact_sha256 TEXT NOT NULL,
                    adapter_sha256 TEXT,
                    evaluation_sha256 TEXT NOT NULL,
                    protected_evaluation_reservation_sha256 TEXT NOT NULL,
                    license_id TEXT NOT NULL,
                    safety_gate TEXT NOT NULL,
                    performance_gate TEXT NOT NULL,
                    transfer_gate TEXT NOT NULL,
                    protected_evaluation_complete INTEGER NOT NULL,
                    created_by TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    record_sha256 TEXT NOT NULL UNIQUE,
                    FOREIGN KEY (training_release_id) REFERENCES actionnet_global_training_releases(release_id)
                );
                CREATE TABLE IF NOT EXISTS c1_model_dispositions (
                    sequence INTEGER PRIMARY KEY AUTOINCREMENT,
                    model_id TEXT NOT NULL,
                    disposition TEXT NOT NULL,
                    rollback_model_id TEXT,
                    evidence_ref_sha256 TEXT NOT NULL,
                    rationale TEXT NOT NULL,
                    actor_id TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    disposition_sha256 TEXT NOT NULL UNIQUE,
                    FOREIGN KEY (model_id) REFERENCES c1_model_versions(model_id)
                );
                CREATE TABLE IF NOT EXISTS learning_network_audit (
                    sequence INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_type TEXT NOT NULL,
                    entity_id TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    previous_hash TEXT NOT NULL,
                    event_hash TEXT NOT NULL UNIQUE,
                    created_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS actionnet_local_export_lookup
                    ON actionnet_local_exports(tenant_id, experience_id);
                CREATE INDEX IF NOT EXISTS c1_disposition_lookup
                    ON c1_model_dispositions(model_id, sequence);
                """
            )
            immutable_tables = (
                "actionnet_local_exports",
                "actionnet_global_records",
                "actionnet_global_events",
                "actionnet_global_training_releases",
                "c1_model_versions",
                "c1_model_dispositions",
                "learning_network_audit",
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
        event_type: str,
        entity_id: str,
        payload: dict[str, Any],
        created_at: str,
    ) -> str:
        previous = connection.execute(
            "SELECT event_hash FROM learning_network_audit ORDER BY sequence DESC LIMIT 1"
        ).fetchone()
        previous_hash = previous["event_hash"] if previous else "GENESIS"
        event = {
            "event_type": event_type,
            "entity_id": entity_id,
            "payload": payload,
            "previous_hash": previous_hash,
            "created_at": created_at,
        }
        event_hash = sha256_json(event)
        connection.execute(
            """INSERT INTO learning_network_audit
               (event_type, entity_id, payload_json, previous_hash, event_hash, created_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (
                event_type,
                entity_id,
                canonical_json(payload),
                previous_hash,
                event_hash,
                created_at,
            ),
        )
        return event_hash

    @staticmethod
    def _normalize_global_experience(value: dict[str, Any]) -> dict[str, Any]:
        normalized = _json_object(value, "normalized_experience")
        required = {
            "institution_type",
            "mechanism_families",
            "trajectory_summary",
            "outcome_summary",
            "generalized_pattern",
            "provenance_commitments",
        }
        missing = sorted(required - set(normalized))
        if missing:
            raise LearningNetworkError(
                "normalized_experience is missing: " + ", ".join(missing)
            )
        if not isinstance(normalized["mechanism_families"], list) or not normalized["mechanism_families"]:
            raise LearningNetworkError("mechanism_families must be a non-empty array")
        normalized["mechanism_families"] = _string_set(
            normalized["mechanism_families"], "mechanism family"
        )
        normalized["institution_type"] = _identifier(
            normalized["institution_type"], "institution_type"
        )
        for key in (
            "trajectory_summary",
            "outcome_summary",
            "generalized_pattern",
            "provenance_commitments",
        ):
            normalized[key] = _json_object(normalized[key], key)
        forbidden = sorted(set(_forbidden_paths(normalized)))
        if forbidden:
            raise LearningNetworkError(
                "global experience contains local, sensitive, or authority fields: "
                + ", ".join(forbidden)
            )
        return {
            "schema_version": "actionnet-global-experience.v1",
            **normalized,
            "raw_payload_included": False,
            "binding_authority": False,
        }

    def promote_local_experience(
        self,
        tenant_id: str,
        request_id: str,
        experience_id: str,
        global_record_id: str,
        normalized_experience: dict[str, Any],
        *,
        rights_basis: str,
        rights_ref_sha256: str,
        privacy_review_sha256: str,
        source_review_sha256: str,
        permitted_uses: Iterable[str],
        deidentification_attested: bool,
        raw_payload_included: bool,
        approved_by: str,
        created_at: str | None = None,
    ) -> dict[str, Any]:
        tenant_id = _identifier(tenant_id, "tenant_id")
        request_id = _identifier(request_id, "request_id")
        experience_id = _identifier(experience_id, "experience_id")
        global_record_id = _identifier(global_record_id, "global_record_id")
        if raw_payload_included:
            raise LearningNetworkError("raw local payload cannot enter Global ActionNet")
        if deidentification_attested is not True:
            raise LearningNetworkError("deidentification attestation is required")
        rights_basis = str(rights_basis).upper()
        if rights_basis not in RIGHTS_BASES:
            raise LearningNetworkError(f"unsupported rights basis: {rights_basis}")
        uses = sorted({str(value).upper() for value in permitted_uses})
        if not uses or not set(uses).issubset(PERMITTED_USES):
            raise LearningNetworkError("permitted_uses must contain registered uses")
        local = self.local_actionnet.experience_state(tenant_id, experience_id)
        if local["protected"]:
            raise LearningNetworkError("protected local experience cannot be promoted")
        if not local["training_eligible"] or not local["overlap_checked"]:
            raise LearningNetworkError(
                "local experience must remain reviewed, overlap-checked, and training eligible"
            )
        normalized = self._normalize_global_experience(normalized_experience)
        normalized_sha256 = sha256_json(normalized)
        source_commitment = sha256_json(
            {
                "tenant_id": tenant_id,
                "experience_id": experience_id,
                "experience_sha256": local["content_sha256"],
            }
        )
        at = _timestamp(created_at or _now(), "created_at")
        request_core = {
            "schema_version": "actionnet-local-export.v1",
            "tenant_id": tenant_id,
            "request_id": request_id,
            "experience_id": experience_id,
            "experience_sha256": local["content_sha256"],
            "global_record_id": global_record_id,
            "normalized_experience_sha256": normalized_sha256,
            "requested_by": _identifier(approved_by, "approved_by"),
            "created_at": at,
            "binding_authority": False,
        }
        request_sha256 = sha256_json(request_core)
        record_core = {
            "schema_version": "actionnet-global-record.v1",
            "global_record_id": global_record_id,
            "source_commitment_sha256": source_commitment,
            "normalized_experience": normalized,
            "normalized_experience_sha256": normalized_sha256,
            "evidence_grade": local["evidence_grade"],
            "rights_basis": rights_basis,
            "rights_ref_sha256": _sha256(rights_ref_sha256, "rights_ref_sha256"),
            "privacy_review_sha256": _sha256(
                privacy_review_sha256, "privacy_review_sha256"
            ),
            "source_review_sha256": _sha256(
                source_review_sha256, "source_review_sha256"
            ),
            "permitted_uses": uses,
            "deidentification_attested": True,
            "raw_payload_included": False,
            "local_training_eligibility_verified": True,
            "approved_by": request_core["requested_by"],
            "created_at": at,
            "training_eligible": "TRAIN" in uses,
            "binding_authority": False,
        }
        record_sha256 = sha256_json(record_core)
        with self._connection() as connection:
            try:
                connection.execute(
                    """INSERT INTO actionnet_local_exports
                       (tenant_id, request_id, experience_id, experience_sha256,
                        global_record_id, normalized_experience_sha256,
                        request_sha256, requested_by, created_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        tenant_id,
                        request_id,
                        experience_id,
                        local["content_sha256"],
                        global_record_id,
                        normalized_sha256,
                        request_sha256,
                        request_core["requested_by"],
                        at,
                    ),
                )
                connection.execute(
                    """INSERT INTO actionnet_global_records
                       (global_record_id, source_commitment_sha256,
                        normalized_experience_json, normalized_experience_sha256,
                        evidence_grade, rights_basis, rights_ref_sha256,
                        privacy_review_sha256, source_review_sha256,
                        permitted_uses_json, approved_by, created_at, record_sha256)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        global_record_id,
                        source_commitment,
                        canonical_json(normalized),
                        normalized_sha256,
                        local["evidence_grade"],
                        rights_basis,
                        record_core["rights_ref_sha256"],
                        record_core["privacy_review_sha256"],
                        record_core["source_review_sha256"],
                        canonical_json(uses),
                        record_core["approved_by"],
                        at,
                        record_sha256,
                    ),
                )
            except sqlite3.IntegrityError as exc:
                raise LearningNetworkError(
                    "local export request, source commitment, or global record already exists"
                ) from exc
            self._audit(
                connection,
                "GLOBAL_EXPERIENCE_PROMOTED",
                global_record_id,
                {
                    "record_sha256": record_sha256,
                    "source_commitment_sha256": source_commitment,
                    "request_sha256": request_sha256,
                    "permitted_uses": uses,
                },
                at,
            )
        return {**record_core, "record_sha256": record_sha256}

    def global_record_state(self, global_record_id: str) -> dict[str, Any]:
        global_record_id = _identifier(global_record_id, "global_record_id")
        with self._connection() as connection:
            row = connection.execute(
                "SELECT * FROM actionnet_global_records WHERE global_record_id = ?",
                (global_record_id,),
            ).fetchone()
            if row is None:
                raise LearningNetworkError("global experience not found")
            events = connection.execute(
                """SELECT * FROM actionnet_global_events
                   WHERE global_record_id = ? ORDER BY sequence""",
                (global_record_id,),
            ).fetchall()
        quarantined = any(event["event_type"] == "QUARANTINED" for event in events)
        result = {
            "schema_version": "actionnet-global-record.v1",
            "global_record_id": row["global_record_id"],
            "source_commitment_sha256": row["source_commitment_sha256"],
            "normalized_experience": json.loads(row["normalized_experience_json"]),
            "normalized_experience_sha256": row["normalized_experience_sha256"],
            "evidence_grade": row["evidence_grade"],
            "rights_basis": row["rights_basis"],
            "rights_ref_sha256": row["rights_ref_sha256"],
            "privacy_review_sha256": row["privacy_review_sha256"],
            "source_review_sha256": row["source_review_sha256"],
            "permitted_uses": json.loads(row["permitted_uses_json"]),
            "deidentification_attested": True,
            "raw_payload_included": False,
            "local_training_eligibility_verified": True,
            "approved_by": row["approved_by"],
            "created_at": row["created_at"],
            "training_eligible": "TRAIN" in json.loads(row["permitted_uses_json"])
            and not quarantined,
            "quarantined": quarantined,
            "record_sha256": row["record_sha256"],
            "binding_authority": False,
        }
        return result

    def quarantine_global_record(
        self,
        global_record_id: str,
        *,
        actor_id: str,
        reason: str,
        evidence_ref_sha256: str,
        created_at: str | None = None,
    ) -> dict[str, Any]:
        global_record_id = _identifier(global_record_id, "global_record_id")
        self.global_record_state(global_record_id)
        at = _timestamp(created_at or _now(), "created_at")
        core = {
            "schema_version": "actionnet-global-event.v1",
            "global_record_id": global_record_id,
            "event_type": "QUARANTINED",
            "actor_id": _identifier(actor_id, "actor_id"),
            "reason": _text(reason, "reason"),
            "evidence_ref_sha256": _sha256(
                evidence_ref_sha256, "evidence_ref_sha256"
            ),
            "created_at": at,
            "binding_authority": False,
        }
        digest = sha256_json(core)
        with self._connection() as connection:
            connection.execute(
                """INSERT INTO actionnet_global_events
                   (global_record_id, event_type, actor_id, reason,
                    evidence_ref_sha256, created_at, event_sha256)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (
                    global_record_id,
                    "QUARANTINED",
                    core["actor_id"],
                    core["reason"],
                    core["evidence_ref_sha256"],
                    at,
                    digest,
                ),
            )
            self._audit(
                connection,
                "GLOBAL_EXPERIENCE_QUARANTINED",
                global_record_id,
                {"event_sha256": digest},
                at,
            )
        return {**core, "event_sha256": digest}

    def _revalidate_local_source(self, global_record_id: str) -> None:
        with self._connection() as connection:
            export = connection.execute(
                """SELECT * FROM actionnet_local_exports
                   WHERE global_record_id = ?""",
                (global_record_id,),
            ).fetchone()
        if export is None:
            raise LearningNetworkError("global record has no local custody mapping")
        local = self.local_actionnet.experience_state(
            export["tenant_id"], export["experience_id"]
        )
        if (
            local["content_sha256"] != export["experience_sha256"]
            or local["protected"]
            or not local["training_eligible"]
            or not local["overlap_checked"]
        ):
            raise LearningNetworkError(
                "local source no longer satisfies promotion or training gates"
            )

    def create_global_training_release(
        self,
        release_id: str,
        global_record_ids: Iterable[str],
        model_target: str,
        *,
        protected_evaluation_reservation_sha256: str,
        dataset_overlap_report_sha256: str,
        release_manager_id: str,
        created_at: str | None = None,
    ) -> dict[str, Any]:
        release_id = _identifier(release_id, "release_id")
        ids = _string_set(global_record_ids, "global_record_id")
        if not ids:
            raise LearningNetworkError("global training release requires records")
        hashes: dict[str, str] = {}
        for global_record_id in ids:
            state = self.global_record_state(global_record_id)
            if not state["training_eligible"] or "TRAIN" not in state["permitted_uses"]:
                raise LearningNetworkError(
                    f"global record is not training eligible: {global_record_id}"
                )
            self._revalidate_local_source(global_record_id)
            hashes[global_record_id] = state["record_sha256"]
        at = _timestamp(created_at or _now(), "created_at")
        core = {
            "schema_version": "actionnet-global-training-release.v1",
            "release_id": release_id,
            "global_record_ids": ids,
            "global_record_hashes": hashes,
            "model_target": _identifier(model_target, "model_target"),
            "protected_evaluation_reservation_sha256": _sha256(
                protected_evaluation_reservation_sha256,
                "protected_evaluation_reservation_sha256",
            ),
            "dataset_overlap_report_sha256": _sha256(
                dataset_overlap_report_sha256, "dataset_overlap_report_sha256"
            ),
            "release_manager_id": _identifier(
                release_manager_id, "release_manager_id"
            ),
            "created_at": at,
            "offline_training_only": True,
            "weight_update_authorized": False,
            "binding_authority": False,
        }
        digest = sha256_json(core)
        with self._connection() as connection:
            try:
                connection.execute(
                    """INSERT INTO actionnet_global_training_releases
                       (release_id, global_record_ids_json,
                        global_record_hashes_json, model_target,
                        protected_evaluation_reservation_sha256,
                        dataset_overlap_report_sha256, release_manager_id,
                        created_at, release_sha256)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        release_id,
                        canonical_json(ids),
                        canonical_json(hashes),
                        core["model_target"],
                        core["protected_evaluation_reservation_sha256"],
                        core["dataset_overlap_report_sha256"],
                        core["release_manager_id"],
                        at,
                        digest,
                    ),
                )
            except sqlite3.IntegrityError as exc:
                raise LearningNetworkError("global training release already exists") from exc
            self._audit(
                connection,
                "GLOBAL_TRAINING_RELEASE_CREATED",
                release_id,
                {"release_sha256": digest, "global_record_count": len(ids)},
                at,
            )
        return {**core, "release_sha256": digest}

    def _training_release(self, release_id: str) -> sqlite3.Row:
        with self._connection() as connection:
            row = connection.execute(
                """SELECT * FROM actionnet_global_training_releases
                   WHERE release_id = ?""",
                (_identifier(release_id, "training_release_id"),),
            ).fetchone()
        if row is None:
            raise LearningNetworkError("global training release not found")
        return row

    def register_c1_version(
        self,
        model_id: str,
        base_model: str,
        model_lineage: str,
        training_release_id: str,
        *,
        artifact_sha256: str,
        evaluation_sha256: str,
        license_id: str,
        safety_gate: str,
        performance_gate: str,
        transfer_gate: str,
        protected_evaluation_complete: bool,
        created_by: str,
        predecessor_model_id: str | None = None,
        adapter_sha256: str | None = None,
        institution_specific_weight_updates_required: bool = False,
        online_weight_updates_allowed: bool = False,
        created_at: str | None = None,
    ) -> dict[str, Any]:
        model_id = _identifier(model_id, "model_id")
        if not model_id.startswith("C1-"):
            raise LearningNetworkError("C1 model IDs must begin with C1-")
        if institution_specific_weight_updates_required:
            raise LearningNetworkError(
                "C1 versions cannot require institution-specific weight updates"
            )
        if online_weight_updates_allowed:
            raise LearningNetworkError("online production weight updates are prohibited")
        release = self._training_release(training_release_id)
        predecessor = (
            _identifier(predecessor_model_id, "predecessor_model_id")
            if predecessor_model_id
            else None
        )
        if predecessor:
            with self._connection() as connection:
                exists = connection.execute(
                    "SELECT 1 FROM c1_model_versions WHERE model_id = ?",
                    (predecessor,),
                ).fetchone()
            if exists is None:
                raise LearningNetworkError("predecessor C1 version is not registered")
        gates = {
            "safety_gate": str(safety_gate).upper(),
            "performance_gate": str(performance_gate).upper(),
            "transfer_gate": str(transfer_gate).upper(),
        }
        for label, value in gates.items():
            if value not in EVALUATION_STATES:
                raise LearningNetworkError(f"unsupported {label}: {value}")
        at = _timestamp(created_at or _now(), "created_at")
        core: dict[str, Any] = {
            "schema_version": "edon-c1-model-manifest.v1",
            "model_id": model_id,
            "architectural_role": "C1_LEARNED_MODEL_LAYER",
            "historical_name": "Cerebrum learned component",
            "predecessor_model_id": predecessor,
            "base_model": _identifier(base_model, "base_model"),
            "model_lineage": _identifier(model_lineage, "model_lineage"),
            "training_release_id": release["release_id"],
            "training_release_sha256": release["release_sha256"],
            "artifact_sha256": _sha256(artifact_sha256, "artifact_sha256"),
            "evaluation_sha256": _sha256(evaluation_sha256, "evaluation_sha256"),
            "protected_evaluation_reservation_sha256": release[
                "protected_evaluation_reservation_sha256"
            ],
            "license_id": _identifier(license_id, "license_id"),
            **gates,
            "protected_evaluation_complete": bool(protected_evaluation_complete),
            "created_by": _identifier(created_by, "created_by"),
            "created_at": at,
            "status": "FROZEN_INTERNAL",
            "deployment_status": "NOT_DEPLOYED",
            "institution_specific_weight_updates_required": False,
            "online_weight_updates_allowed": False,
            "binding_authority": False,
        }
        if adapter_sha256 is not None:
            core["adapter_sha256"] = _sha256(adapter_sha256, "adapter_sha256")
        digest = sha256_json(core)
        with self._connection() as connection:
            try:
                connection.execute(
                    """INSERT INTO c1_model_versions
                       (model_id, predecessor_model_id, base_model,
                        model_lineage, training_release_id,
                        training_release_sha256, artifact_sha256,
                        adapter_sha256, evaluation_sha256,
                        protected_evaluation_reservation_sha256, license_id,
                        safety_gate, performance_gate, transfer_gate,
                        protected_evaluation_complete, created_by, created_at,
                        record_sha256)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        model_id,
                        predecessor,
                        core["base_model"],
                        core["model_lineage"],
                        release["release_id"],
                        release["release_sha256"],
                        core["artifact_sha256"],
                        core.get("adapter_sha256"),
                        core["evaluation_sha256"],
                        core["protected_evaluation_reservation_sha256"],
                        core["license_id"],
                        core["safety_gate"],
                        core["performance_gate"],
                        core["transfer_gate"],
                        int(core["protected_evaluation_complete"]),
                        core["created_by"],
                        at,
                        digest,
                    ),
                )
            except sqlite3.IntegrityError as exc:
                raise LearningNetworkError("C1 model version already exists") from exc
            self._audit(
                connection,
                "C1_VERSION_REGISTERED",
                model_id,
                {
                    "record_sha256": digest,
                    "training_release_sha256": release["release_sha256"],
                },
                at,
            )
        return {**core, "record_sha256": digest}

    def c1_version_state(self, model_id: str) -> dict[str, Any]:
        model_id = _identifier(model_id, "model_id")
        with self._connection() as connection:
            row = connection.execute(
                "SELECT * FROM c1_model_versions WHERE model_id = ?", (model_id,)
            ).fetchone()
            if row is None:
                raise LearningNetworkError("C1 model version not found")
            events = connection.execute(
                """SELECT * FROM c1_model_dispositions
                   WHERE model_id = ? ORDER BY sequence""",
                (model_id,),
            ).fetchall()
        latest = events[-1]["disposition"] if events else "NOT_DEPLOYED"
        return {
            "model_id": row["model_id"],
            "predecessor_model_id": row["predecessor_model_id"],
            "model_lineage": row["model_lineage"],
            "training_release_id": row["training_release_id"],
            "training_release_sha256": row["training_release_sha256"],
            "artifact_sha256": row["artifact_sha256"],
            "adapter_sha256": row["adapter_sha256"],
            "evaluation_sha256": row["evaluation_sha256"],
            "safety_gate": row["safety_gate"],
            "performance_gate": row["performance_gate"],
            "transfer_gate": row["transfer_gate"],
            "protected_evaluation_complete": bool(row["protected_evaluation_complete"]),
            "current_disposition": latest,
            "record_sha256": row["record_sha256"],
            "institution_specific_weight_updates_required": False,
            "online_weight_updates_allowed": False,
            "binding_authority": False,
        }

    def record_c1_disposition(
        self,
        model_id: str,
        disposition: str,
        *,
        evidence_ref_sha256: str,
        rationale: str,
        actor_id: str,
        rollback_model_id: str | None = None,
        created_at: str | None = None,
    ) -> dict[str, Any]:
        model = self.c1_version_state(model_id)
        disposition = str(disposition).upper()
        if disposition not in C1_DISPOSITIONS:
            raise LearningNetworkError(f"unsupported C1 disposition: {disposition}")
        if disposition in {"SHADOW_ELIGIBLE", "DEPLOYMENT_ELIGIBLE"}:
            if not model["protected_evaluation_complete"]:
                raise LearningNetworkError("protected evaluation must be complete")
            if model["safety_gate"] != "PASS" or model["performance_gate"] != "PASS":
                raise LearningNetworkError("safety and performance gates must pass")
            if model["transfer_gate"] not in {"PASS", "NOT_APPLICABLE"}:
                raise LearningNetworkError("transfer gate must pass or be not applicable")
        rollback = (
            _identifier(rollback_model_id, "rollback_model_id")
            if rollback_model_id
            else None
        )
        if disposition == "ROLLBACK_REQUIRED":
            if not rollback:
                raise LearningNetworkError("rollback disposition requires a target model")
            if rollback == model["model_id"]:
                raise LearningNetworkError("rollback target must differ from the current model")
            self.c1_version_state(rollback)
        elif rollback is not None:
            raise LearningNetworkError("rollback_model_id is valid only for rollback")
        at = _timestamp(created_at or _now(), "created_at")
        core = {
            "schema_version": "edon-c1-model-disposition.v1",
            "model_id": model["model_id"],
            "disposition": disposition,
            "rollback_model_id": rollback,
            "evidence_ref_sha256": _sha256(
                evidence_ref_sha256, "evidence_ref_sha256"
            ),
            "rationale": _text(rationale, "rationale"),
            "actor_id": _identifier(actor_id, "actor_id"),
            "created_at": at,
            "operational_effect": False,
            "binding_authority": False,
        }
        digest = sha256_json(core)
        with self._connection() as connection:
            connection.execute(
                """INSERT INTO c1_model_dispositions
                   (model_id, disposition, rollback_model_id,
                    evidence_ref_sha256, rationale, actor_id, created_at,
                    disposition_sha256)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    model["model_id"],
                    disposition,
                    rollback,
                    core["evidence_ref_sha256"],
                    core["rationale"],
                    core["actor_id"],
                    at,
                    digest,
                ),
            )
            self._audit(
                connection,
                "C1_DISPOSITION_RECORDED",
                model["model_id"],
                {"disposition": disposition, "disposition_sha256": digest},
                at,
            )
        return {**core, "disposition_sha256": digest}

    def audit_events(self) -> list[dict[str, Any]]:
        with self._connection() as connection:
            rows = connection.execute(
                "SELECT * FROM learning_network_audit ORDER BY sequence"
            ).fetchall()
        return [
            {**dict(row), "payload": json.loads(row["payload_json"])} for row in rows
        ]

    def verify_audit_chain(self) -> bool:
        previous = "GENESIS"
        for row in self.audit_events():
            event = {
                "event_type": row["event_type"],
                "entity_id": row["entity_id"],
                "payload": row["payload"],
                "previous_hash": row["previous_hash"],
                "created_at": row["created_at"],
            }
            if row["previous_hash"] != previous or sha256_json(event) != row["event_hash"]:
                return False
            previous = row["event_hash"]
        return True

    def counts(self) -> dict[str, int]:
        tables = {
            "local_exports": "actionnet_local_exports",
            "global_records": "actionnet_global_records",
            "global_training_releases": "actionnet_global_training_releases",
            "c1_versions": "c1_model_versions",
            "c1_dispositions": "c1_model_dispositions",
        }
        with self._connection() as connection:
            return {
                key: int(connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])
                for key, table in tables.items()
            }


__all__ = [
    "C1_DISPOSITIONS",
    "GovernedLearningNetwork",
    "LearningNetworkError",
    "PERMITTED_USES",
    "RIGHTS_BASES",
]