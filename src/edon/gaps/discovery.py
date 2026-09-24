"""Convert repeated decision disagreements into reviewable IR amendment proposals."""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from edon.common.hashing import sha256_json


def _gap_type(record: dict[str, Any]) -> str:
    failed = " ".join(record.get("runtime_failed_conditions", [])).casefold()
    decisions = record["decisions"]
    if "author" in failed or "role" in failed:
        return "MISSING_AUTHORITY_RELATIONSHIP"
    if "evidence" in failed or "requires" in failed or "check" in failed:
        return "MISSING_EVIDENCE_OR_VALIDITY_RULE"
    if "deadline" in failed or "window" in failed or "time" in failed:
        return "TEMPORAL_RULE_MISMATCH"
    if decisions["human"] != decisions["existing_system"]:
        return "NORMATIVE_OPERATIONAL_DIVERGENCE"
    if decisions["human"] != decisions["cerebrum"]:
        return "MODEL_REASONING_GAP"
    return "UNDOCUMENTED_EXCEPTION"


def discover_gaps(shadow_report: dict[str, Any], *, minimum_repetitions: int = 2) -> dict[str, Any]:
    groups: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for record in shadow_report.get("records", []):
        if record.get("unanimous"):
            continue
        groups[(str(record.get("mechanism_id")), _gap_type(record))].append(record)
    proposals: list[dict[str, Any]] = []
    for (mechanism_id, gap_type), records in sorted(groups.items()):
        if len(records) < minimum_repetitions:
            continue
        evidence_ids = sorted(record["shadow_id"] for record in records)
        identity = {
            "mechanism_id": mechanism_id,
            "gap_type": gap_type,
            "evidence_ids": evidence_ids,
            "shadow_report_sha256": shadow_report.get("report_sha256"),
        }
        proposals.append({
            "proposal_id": "gap-" + sha256_json(identity).split(":", 1)[1][:20],
            "mechanism_id": mechanism_id,
            "gap_type": gap_type,
            "evidence_shadow_ids": evidence_ids,
            "occurrences": len(records),
            "recommended_action": "REVIEW_AND_PROPOSE_IR_AMENDMENT",
            "approved": False,
            "binding_authority": False,
        })
    return {
        "schema_version": "edon-gap-discovery.v1",
        "source_shadow_sha256": shadow_report.get("report_sha256"),
        "minimum_repetitions": minimum_repetitions,
        "proposal_count": len(proposals),
        "proposals": proposals,
        "binding_authority": False,
        "claim_boundary": "Heuristic amendment proposals requiring source review and authorized approval.",
    }