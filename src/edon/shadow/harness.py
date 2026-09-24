"""Compare human, incumbent-system, Cerebrum, and deterministic runtime decisions."""

from __future__ import annotations

from collections import Counter
from typing import Any

from edon.common.hashing import sha256_json


VALID_DECISIONS = {"ALLOW", "DENY", "ABSTAIN", "CONTESTED", "INVALID"}


def run_shadow_comparison(records: list[dict[str, Any]]) -> dict[str, Any]:
    normalized: list[dict[str, Any]] = []
    pairwise = Counter()
    disagreement_signatures = Counter()
    for index, record in enumerate(records):
        decisions = {
            "human": str(record.get("human_decision")),
            "existing_system": str(record.get("system_decision")),
            "cerebrum": str(record.get("cerebrum_decision")),
            "runtime": str(record.get("runtime_decision")),
        }
        if any(decision not in VALID_DECISIONS for decision in decisions.values()):
            raise ValueError(f"shadow record {index} contains an invalid decision")
        pairwise["human_system"] += decisions["human"] == decisions["existing_system"]
        pairwise["human_cerebrum"] += decisions["human"] == decisions["cerebrum"]
        pairwise["human_runtime"] += decisions["human"] == decisions["runtime"]
        unanimous = len(set(decisions.values())) == 1
        signature = "|".join(f"{key}={value}" for key, value in decisions.items())
        if not unanimous:
            disagreement_signatures[signature] += 1
        context = record.get("context", {})
        normalized.append({
            "shadow_id": record.get("shadow_id") or "shadow-" + sha256_json({"index": index, "context": context}).split(":", 1)[1][:20],
            "mechanism_id": record.get("mechanism_id"),
            "context_sha256": sha256_json(context),
            "context": context,
            "decisions": decisions,
            "runtime_failed_conditions": list(record.get("runtime_failed_conditions", [])),
            "unanimous": unanimous,
        })
    total = len(normalized)
    disagreements = [row for row in normalized if not row["unanimous"]]
    return {
        "schema_version": "edon-shadow-report.v1",
        "records": normalized,
        "summary": {
            "record_count": total,
            "unanimous_count": total - len(disagreements),
            "disagreement_count": len(disagreements),
            "human_system_agreement": pairwise["human_system"] / total if total else 0.0,
            "human_cerebrum_agreement": pairwise["human_cerebrum"] / total if total else 0.0,
            "human_runtime_agreement": pairwise["human_runtime"] / total if total else 0.0,
            "disagreement_signatures": dict(sorted(disagreement_signatures.items())),
        },
        "report_sha256": sha256_json(normalized),
        "binding_authority": False,
        "claim_boundary": "Shadow comparison only; no decisions are committed by this harness.",
    }