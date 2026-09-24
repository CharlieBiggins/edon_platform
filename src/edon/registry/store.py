"""SQLite-backed candidate review and promotion registry with hash-chained audit."""

from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import Any

from edon.common.hashing import canonical_json, sha256_json


class RegistryError(RuntimeError):
    pass


class ReviewDecision(StrEnum):
    APPROVE = "APPROVE"
    REJECT = "REJECT"
    REVISION_REQUIRED = "REVISION_REQUIRED"


def _now() -> str:
    return datetime.now(UTC).isoformat()


class ReviewRegistry:
    """Transactional store for compiler candidates and approved mechanisms."""

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
                CREATE TABLE IF NOT EXISTS compiler_runs (
                    run_id TEXT PRIMARY KEY,
                    institution_id TEXT NOT NULL,
                    input_sha256 TEXT NOT NULL,
                    output_sha256 TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS candidates (
                    candidate_id TEXT PRIMARY KEY,
                    run_id TEXT NOT NULL REFERENCES compiler_runs(run_id),
                    mechanism_id TEXT NOT NULL,
                    mechanism_version TEXT NOT NULL,
                    risk_class TEXT NOT NULL,
                    candidate_sha256 TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS reviews (
                    review_id TEXT PRIMARY KEY,
                    candidate_id TEXT NOT NULL REFERENCES candidates(candidate_id),
                    reviewer_id TEXT NOT NULL,
                    reviewer_role TEXT NOT NULL,
                    decision TEXT NOT NULL,
                    rationale TEXT NOT NULL,
                    resolutions_json TEXT NOT NULL,
                    candidate_sha256 TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    UNIQUE(candidate_id, reviewer_id)
                );
                CREATE TABLE IF NOT EXISTS mechanisms (
                    mechanism_id TEXT NOT NULL,
                    version TEXT NOT NULL,
                    candidate_id TEXT NOT NULL REFERENCES candidates(candidate_id),
                    artifact_sha256 TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    active INTEGER NOT NULL,
                    promoted_at TEXT NOT NULL,
                    PRIMARY KEY(mechanism_id, version)
                );
                CREATE TABLE IF NOT EXISTS audit_events (
                    sequence INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_type TEXT NOT NULL,
                    entity_id TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    previous_hash TEXT NOT NULL,
                    event_hash TEXT NOT NULL UNIQUE,
                    created_at TEXT NOT NULL
                );
                CREATE TRIGGER IF NOT EXISTS audit_events_no_update
                BEFORE UPDATE ON audit_events BEGIN
                    SELECT RAISE(ABORT, 'audit events are immutable');
                END;
                CREATE TRIGGER IF NOT EXISTS audit_events_no_delete
                BEFORE DELETE ON audit_events BEGIN
                    SELECT RAISE(ABORT, 'audit events are immutable');
                END;
                CREATE TRIGGER IF NOT EXISTS reviews_no_update
                BEFORE UPDATE ON reviews BEGIN
                    SELECT RAISE(ABORT, 'reviews are immutable');
                END;
                CREATE TRIGGER IF NOT EXISTS reviews_no_delete
                BEFORE DELETE ON reviews BEGIN
                    SELECT RAISE(ABORT, 'reviews are immutable');
                END;
                """
            )
        self.path.chmod(0o600)

    def _append_audit(
        self,
        connection: sqlite3.Connection,
        event_type: str,
        entity_id: str,
        payload: dict[str, Any],
        timestamp: str,
    ) -> str:
        previous = connection.execute(
            "SELECT event_hash FROM audit_events ORDER BY sequence DESC LIMIT 1"
        ).fetchone()
        previous_hash = previous["event_hash"] if previous else "GENESIS"
        event = {
            "event_type": event_type,
            "entity_id": entity_id,
            "payload": payload,
            "previous_hash": previous_hash,
            "created_at": timestamp,
        }
        event_hash = sha256_json(event)
        connection.execute(
            """INSERT INTO audit_events
               (event_type, entity_id, payload_json, previous_hash, event_hash, created_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (event_type, entity_id, canonical_json(payload), previous_hash, event_hash, timestamp),
        )
        return event_hash

    def register_compiler_run(self, report: dict[str, Any], *, timestamp: str | None = None) -> list[str]:
        if report.get("binding_authority") is not False:
            raise RegistryError("compiler report must be explicitly non-binding")
        if not report.get("qualification", {}).get("passed"):
            raise RegistryError("compiler report must pass technical qualification")
        run_id = str(report.get("compiler_run_id", ""))
        if not run_id:
            raise RegistryError("compiler report has no run identity")
        candidates = report.get("candidates")
        if not isinstance(candidates, list) or not candidates:
            raise RegistryError("compiler report has no candidates")
        created_at = timestamp or _now()
        input_hash = report.get("compiler_manifest", {}).get("input_sha256")
        output_hash = report.get("compiler_manifest", {}).get("compiled_payload_sha256")
        if not isinstance(input_hash, str) or not isinstance(output_hash, str):
            raise RegistryError("compiler report is missing manifest hashes")

        registered: list[str] = []
        with self._connection() as connection:
            existing = connection.execute(
                "SELECT output_sha256 FROM compiler_runs WHERE run_id = ?", (run_id,)
            ).fetchone()
            if existing:
                if existing["output_sha256"] != output_hash:
                    raise RegistryError("compiler run identity is already bound to different bytes")
                return [
                    row["candidate_id"] for row in connection.execute(
                        "SELECT candidate_id FROM candidates WHERE run_id = ? ORDER BY candidate_id", (run_id,)
                    )
                ]
            connection.execute(
                """INSERT INTO compiler_runs
                   (run_id, institution_id, input_sha256, output_sha256, payload_json, created_at)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (
                    run_id,
                    str(report.get("institution_id", "")),
                    input_hash,
                    output_hash,
                    canonical_json(report),
                    created_at,
                ),
            )
            self._append_audit(
                connection,
                "COMPILER_RUN_REGISTERED",
                run_id,
                {"input_sha256": input_hash, "output_sha256": output_hash},
                created_at,
            )
            for candidate in candidates:
                candidate_id = str(candidate.get("candidate_id", ""))
                mechanism = candidate.get("mechanism", {})
                if not candidate_id or candidate.get("binding_authority") is not False:
                    raise RegistryError("candidate is missing identity or is not explicitly non-binding")
                if mechanism.get("approved") is not False:
                    raise RegistryError("only unapproved compiler candidates may be registered")
                candidate_hash = sha256_json(candidate)
                connection.execute(
                    """INSERT INTO candidates
                       (candidate_id, run_id, mechanism_id, mechanism_version, risk_class,
                        candidate_sha256, payload_json, status, created_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        candidate_id,
                        run_id,
                        str(mechanism.get("mechanism_id", "")),
                        str(mechanism.get("version", "")),
                        str(mechanism.get("risk_class", "UNCLASSIFIED")),
                        candidate_hash,
                        canonical_json(candidate),
                        "REGISTERED",
                        created_at,
                    ),
                )
                self._append_audit(
                    connection,
                    "CANDIDATE_REGISTERED",
                    candidate_id,
                    {"candidate_sha256": candidate_hash, "run_id": run_id},
                    created_at,
                )
                registered.append(candidate_id)
        return registered

    def _candidate_row(self, connection: sqlite3.Connection, candidate_id: str) -> sqlite3.Row:
        row = connection.execute(
            "SELECT * FROM candidates WHERE candidate_id = ?", (candidate_id,)
        ).fetchone()
        if not row:
            raise RegistryError(f"unknown candidate: {candidate_id}")
        return row

    @staticmethod
    def _required_approvals(risk_class: str) -> int:
        if risk_class == "CRITICAL":
            return 3
        return 2 if risk_class == "HIGH" else 1

    def _candidate_status(self, connection: sqlite3.Connection, candidate: sqlite3.Row) -> str:
        reviews = list(connection.execute(
            "SELECT * FROM reviews WHERE candidate_id = ? ORDER BY created_at, review_id",
            (candidate["candidate_id"],),
        ))
        if any(row["decision"] == ReviewDecision.REJECT.value for row in reviews):
            return "REJECTED"
        if any(row["decision"] == ReviewDecision.REVISION_REQUIRED.value for row in reviews):
            return "REVISION_REQUIRED"
        approvals = [row for row in reviews if row["decision"] == ReviewDecision.APPROVE.value]
        approval_roles = {row["reviewer_role"] for row in approvals}
        payload = json.loads(candidate["payload_json"])
        conflicts = set(payload.get("conflict_ids", []))
        resolved = {
            conflict_id
            for row in approvals
            for conflict_id in json.loads(row["resolutions_json"]).keys()
        }
        role_separation_passes = True
        if candidate["risk_class"] == "HIGH":
            role_separation_passes = {"DOMAIN_REVIEWER", "SAFETY_REVIEWER"} <= approval_roles
        elif candidate["risk_class"] == "CRITICAL":
            role_separation_passes = {
                "DOMAIN_REVIEWER", "SAFETY_REVIEWER", "EXECUTIVE_RISK_OWNER"
            } <= approval_roles
        if (
            len(approvals) >= self._required_approvals(candidate["risk_class"])
            and role_separation_passes
            and conflicts <= resolved
        ):
            return "READY_TO_PROMOTE"
        return "UNDER_REVIEW" if reviews else "REGISTERED"

    def submit_review(
        self,
        candidate_id: str,
        reviewer_id: str,
        reviewer_role: str,
        decision: ReviewDecision | str,
        rationale: str,
        *,
        resolutions: dict[str, str] | None = None,
        timestamp: str | None = None,
    ) -> dict[str, Any]:
        try:
            decision = ReviewDecision(decision)
        except ValueError as exc:
            raise RegistryError("unsupported review decision") from exc
        if not reviewer_id.strip() or not reviewer_role.strip() or not rationale.strip():
            raise RegistryError("reviewer identity, role, and rationale are required")
        resolutions = resolutions or {}
        created_at = timestamp or _now()
        with self._connection() as connection:
            candidate = self._candidate_row(connection, candidate_id)
            if candidate["status"] in {"PROMOTED", "REJECTED"}:
                raise RegistryError(f"candidate cannot be reviewed in status {candidate['status']}")
            payload = json.loads(candidate["payload_json"])
            known_conflicts = set(payload.get("conflict_ids", []))
            if not set(resolutions) <= known_conflicts:
                raise RegistryError("review resolutions reference unknown conflicts")
            if decision is ReviewDecision.APPROVE and known_conflicts and not resolutions:
                raise RegistryError("approving a conflicted candidate requires explicit resolutions")
            review_identity = {
                "candidate_id": candidate_id,
                "reviewer_id": reviewer_id,
                "decision": decision.value,
                "candidate_sha256": candidate["candidate_sha256"],
                "created_at": created_at,
            }
            review_id = "review-" + sha256_json(review_identity).split(":", 1)[1][:20]
            try:
                connection.execute(
                    """INSERT INTO reviews
                       (review_id, candidate_id, reviewer_id, reviewer_role, decision, rationale,
                        resolutions_json, candidate_sha256, created_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        review_id,
                        candidate_id,
                        reviewer_id,
                        reviewer_role,
                        decision.value,
                        rationale,
                        canonical_json(resolutions),
                        candidate["candidate_sha256"],
                        created_at,
                    ),
                )
            except sqlite3.IntegrityError as exc:
                raise RegistryError("reviewer has already reviewed this candidate") from exc
            self._append_audit(
                connection,
                "CANDIDATE_REVIEWED",
                candidate_id,
                {
                    "review_id": review_id,
                    "reviewer_id": reviewer_id,
                    "reviewer_role": reviewer_role,
                    "decision": decision.value,
                    "resolutions": resolutions,
                    "candidate_sha256": candidate["candidate_sha256"],
                },
                created_at,
            )
            status = self._candidate_status(connection, candidate)
            connection.execute(
                "UPDATE candidates SET status = ? WHERE candidate_id = ?", (status, candidate_id)
            )
        return {"review_id": review_id, "candidate_id": candidate_id, "status": status}

    def promote(
        self,
        candidate_id: str,
        promoter_id: str,
        *,
        timestamp: str | None = None,
    ) -> dict[str, Any]:
        if not promoter_id.strip():
            raise RegistryError("promoter identity is required")
        promoted_at = timestamp or _now()
        with self._connection() as connection:
            candidate = self._candidate_row(connection, candidate_id)
            status = self._candidate_status(connection, candidate)
            if status != "READY_TO_PROMOTE":
                raise RegistryError(f"candidate is not ready to promote: {status}")
            payload = json.loads(candidate["payload_json"])
            mechanism = dict(payload["mechanism"])
            reviews = list(connection.execute(
                "SELECT * FROM reviews WHERE candidate_id = ? ORDER BY created_at, review_id",
                (candidate_id,),
            ))
            approvals = [row for row in reviews if row["decision"] == ReviewDecision.APPROVE.value]
            resolutions = {
                key: value
                for row in approvals
                for key, value in json.loads(row["resolutions_json"]).items()
            }
            metadata = dict(mechanism.get("metadata", {}))
            metadata.update({
                "promoted_from_candidate": candidate_id,
                "candidate_sha256": candidate["candidate_sha256"],
                "approval_ids": [row["review_id"] for row in approvals],
                "resolved_conflicts": resolutions,
                "promoter_id": promoter_id,
            })
            mechanism["metadata"] = metadata
            mechanism["approved"] = True
            mechanism["facts"] = payload.get("facts", [])
            mechanism["binding_authority"] = False
            artifact_hash = sha256_json(mechanism)
            mechanism_id = str(mechanism["mechanism_id"])
            version = str(mechanism["version"])
            connection.execute(
                "UPDATE mechanisms SET active = 0 WHERE mechanism_id = ?", (mechanism_id,)
            )
            try:
                connection.execute(
                    """INSERT INTO mechanisms
                       (mechanism_id, version, candidate_id, artifact_sha256, payload_json, active, promoted_at)
                       VALUES (?, ?, ?, ?, ?, 1, ?)""",
                    (
                        mechanism_id,
                        version,
                        candidate_id,
                        artifact_hash,
                        canonical_json(mechanism),
                        promoted_at,
                    ),
                )
            except sqlite3.IntegrityError as exc:
                raise RegistryError("mechanism version has already been promoted") from exc
            connection.execute(
                "UPDATE candidates SET status = 'PROMOTED' WHERE candidate_id = ?", (candidate_id,)
            )
            self._append_audit(
                connection,
                "MECHANISM_PROMOTED",
                f"{mechanism_id}@{version}",
                {
                    "candidate_id": candidate_id,
                    "artifact_sha256": artifact_hash,
                    "promoter_id": promoter_id,
                    "approval_ids": metadata["approval_ids"],
                },
                promoted_at,
            )
        return mechanism

    def rollback(
        self,
        mechanism_id: str,
        target_version: str,
        actor_id: str,
        rationale: str,
        *,
        timestamp: str | None = None,
    ) -> dict[str, Any]:
        changed_at = timestamp or _now()
        with self._connection() as connection:
            target = connection.execute(
                "SELECT * FROM mechanisms WHERE mechanism_id = ? AND version = ?",
                (mechanism_id, target_version),
            ).fetchone()
            if not target:
                raise RegistryError("rollback target does not exist")
            connection.execute("UPDATE mechanisms SET active = 0 WHERE mechanism_id = ?", (mechanism_id,))
            connection.execute(
                "UPDATE mechanisms SET active = 1 WHERE mechanism_id = ? AND version = ?",
                (mechanism_id, target_version),
            )
            self._append_audit(
                connection,
                "MECHANISM_ROLLED_BACK",
                f"{mechanism_id}@{target_version}",
                {"actor_id": actor_id, "rationale": rationale},
                changed_at,
            )
        return json.loads(target["payload_json"])

    def get_candidate(self, candidate_id: str) -> dict[str, Any]:
        with self._connection() as connection:
            row = self._candidate_row(connection, candidate_id)
            payload = json.loads(row["payload_json"])
            payload["registry_status"] = row["status"]
            payload["candidate_sha256"] = row["candidate_sha256"]
            return payload

    def list_candidates(self) -> list[dict[str, Any]]:
        with self._connection() as connection:
            return [
                {
                    "candidate_id": row["candidate_id"],
                    "run_id": row["run_id"],
                    "mechanism_id": row["mechanism_id"],
                    "version": row["mechanism_version"],
                    "risk_class": row["risk_class"],
                    "status": row["status"],
                    "candidate_sha256": row["candidate_sha256"],
                }
                for row in connection.execute("SELECT * FROM candidates ORDER BY candidate_id")
            ]

    def get_mechanism(self, mechanism_id: str, version: str | None = None) -> dict[str, Any]:
        with self._connection() as connection:
            if version is None:
                row = connection.execute(
                    "SELECT * FROM mechanisms WHERE mechanism_id = ? AND active = 1",
                    (mechanism_id,),
                ).fetchone()
            else:
                row = connection.execute(
                    "SELECT * FROM mechanisms WHERE mechanism_id = ? AND version = ?",
                    (mechanism_id, version),
                ).fetchone()
            if not row:
                raise RegistryError("approved mechanism not found")
            return json.loads(row["payload_json"])

    def list_mechanisms(self) -> list[dict[str, Any]]:
        with self._connection() as connection:
            return [
                {
                    "mechanism_id": row["mechanism_id"],
                    "version": row["version"],
                    "candidate_id": row["candidate_id"],
                    "artifact_sha256": row["artifact_sha256"],
                    "active": bool(row["active"]),
                    "promoted_at": row["promoted_at"],
                }
                for row in connection.execute(
                    "SELECT * FROM mechanisms ORDER BY mechanism_id, version"
                )
            ]

    def audit_events(self) -> list[dict[str, Any]]:
        with self._connection() as connection:
            return [
                {
                    "sequence": row["sequence"],
                    "event_type": row["event_type"],
                    "entity_id": row["entity_id"],
                    "payload": json.loads(row["payload_json"]),
                    "previous_hash": row["previous_hash"],
                    "event_hash": row["event_hash"],
                    "created_at": row["created_at"],
                }
                for row in connection.execute("SELECT * FROM audit_events ORDER BY sequence")
            ]

    def verify_audit_chain(self) -> bool:
        previous_hash = "GENESIS"
        for row in self.audit_events():
            if row["previous_hash"] != previous_hash:
                return False
            expected = sha256_json({
                "event_type": row["event_type"],
                "entity_id": row["entity_id"],
                "payload": row["payload"],
                "previous_hash": row["previous_hash"],
                "created_at": row["created_at"],
            })
            if expected != row["event_hash"]:
                return False
            previous_hash = row["event_hash"]
        return True