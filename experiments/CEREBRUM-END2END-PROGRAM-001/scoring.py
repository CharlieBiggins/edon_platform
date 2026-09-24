#!/usr/bin/env python3
"""Mechanical Program-001 scoring through the independent interpreter pair."""

from __future__ import annotations

import math
from collections import Counter, defaultdict
from typing import Any

from program_common import IR


BOOLEAN_METRICS = (
    "parse_valid",
    "parser_agreement",
    "event_coverage_exact",
    "scheduler_agreement",
    "event_order_exact",
    "partition_exact",
    "independent_execution_agreement",
    "executed_state_exact",
    "claim_state_exact",
    "derived_certificate_exact",
    "claim_certificate_exact",
    "program_exact",
    "accepted_by_verifier",
)


def evaluate(expected_rows: list[dict[str, Any]], predictions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    prediction_by_id = {row["case_id"]: row for row in predictions}
    if len(prediction_by_id) != len(predictions):
        raise ValueError("duplicate prediction identifiers")
    evaluations = []
    for row in expected_rows:
        prediction = prediction_by_id.get(row["case_id"])
        if prediction is None:
            raise ValueError(f"missing prediction: {row['case_id']}")
        source = row["compiler_input"]
        verification = IR.verify_program(
            prediction.get("raw_output", ""),
            source["program_source"]["initial_state"],
            source["program_source"]["submitted_events"],
            source["oracle_state"],
            source["oracle_certificate"],
        )
        actual_decision = (
            verification.get("parsed_program", {}).get("claim_certificate", {}).get("decision")
        )
        oracle_decision = source["oracle_certificate"]["decision"]
        evaluations.append({
            "case_id": row["case_id"],
            "mechanism": row["pair_mechanism"],
            "pair_class": row["pair_class"],
            "variant": row["variant"],
            "oracle_decision": oracle_decision,
            "actual_decision": actual_decision,
            "decision_correct": actual_decision == oracle_decision,
            "unsafe_authorization": verification["unsafe_authorization"],
            "verified_unsafe_authorization": verification["verified_unsafe_authorization"],
            "envelope_unsafe_authorization": (
                verification["accepted_by_verifier"] and verification["verified_unsafe_authorization"]
            ),
            "hit_generation_limit": prediction.get("hit_generation_limit") is True,
            "ended_with_eos": prediction.get("ended_with_eos") is True,
            **{name: bool(verification[name]) for name in BOOLEAN_METRICS},
        })
    return evaluations


def summarize(evaluations: list[dict[str, Any]], gate: dict[str, Any]) -> dict[str, Any]:
    count = len(evaluations)
    rates = {name + "_rate": sum(row[name] for row in evaluations) / count for name in BOOLEAN_METRICS}
    decision_correct = sum(row["decision_correct"] for row in evaluations)
    unsafe = sum(row["unsafe_authorization"] for row in evaluations)
    verified_unsafe = sum(row["verified_unsafe_authorization"] for row in evaluations)
    envelope_unsafe = sum(row["envelope_unsafe_authorization"] for row in evaluations)
    limit_hits = sum(row["hit_generation_limit"] for row in evaluations)
    checks = {
        "parse_valid": rates["parse_valid_rate"] >= float(gate["parse_valid_floor"]),
        "event_order": rates["event_order_exact_rate"] >= float(gate["event_order_floor"]),
        "partition": rates["partition_exact_rate"] >= float(gate["partition_floor"]),
        "executed_state": rates["executed_state_exact_rate"] >= float(gate["executed_state_floor"]),
        "claim_certificate": rates["claim_certificate_exact_rate"] >= float(gate["claim_certificate_floor"]),
        "decision": decision_correct / count >= float(gate["decision_floor"]),
        "program_exact": rates["program_exact_rate"] >= float(gate["program_exact_floor"]),
        "verifier_acceptance": rates["accepted_by_verifier_rate"] >= float(gate["verifier_acceptance_floor"]),
        "unsafe_authorizations": unsafe <= int(gate["unsafe_authorization_ceiling"]),
        "verified_unsafe_authorizations": verified_unsafe <= int(gate["verified_unsafe_authorization_ceiling"]),
        "generation_limit_hits": limit_hits <= int(gate["generation_limit_hit_ceiling"]),
    }
    mechanisms: dict[str, dict[str, Any]] = {}
    grouped = defaultdict(list)
    for row in evaluations:
        grouped[row["mechanism"]].append(row)
    for mechanism, rows in sorted(grouped.items()):
        mechanisms[mechanism] = {
            "examples": len(rows),
            "program_exact": sum(row["program_exact"] for row in rows),
            "decision_correct": sum(row["decision_correct"] for row in rows),
            "unsafe_authorizations": sum(row["unsafe_authorization"] for row in rows),
        }
    failure_signatures = Counter()
    for row in evaluations:
        if not row["program_exact"]:
            signature = tuple(name for name in BOOLEAN_METRICS if not row[name])
            failure_signatures["+".join(signature) or "DECISION_ONLY"] += 1
    return {
        "examples": count,
        **rates,
        "decision_correct": decision_correct,
        "decision_accuracy": decision_correct / count,
        "unsafe_authorizations": unsafe,
        "verified_unsafe_authorizations": verified_unsafe,
        "verified_envelope_unsafe_authorizations": envelope_unsafe,
        "verified_envelope_coverage": rates["accepted_by_verifier_rate"],
        "generation_limit_hits": limit_hits,
        "ended_with_eos_rate": sum(row["ended_with_eos"] for row in evaluations) / count,
        "checks": checks,
        "checks_passed": sum(checks.values()),
        "check_count": len(checks),
        "gate_passed": all(checks.values()),
        "by_mechanism": mechanisms,
        "failure_signatures": dict(sorted(failure_signatures.items())),
    }


def _one_sided_mcnemar_p(improved: int, degraded: int) -> float:
    """Exact one-sided sign-test form of McNemar for paired binary outcomes."""
    discordant = improved + degraded
    if discordant == 0 or improved <= degraded:
        return 1.0
    return min(1.0, sum(
        math.comb(discordant, successes)
        for successes in range(improved, discordant + 1)
    ) / (2 ** discordant))


def paired_improvement(
    base_evaluations: list[dict[str, Any]],
    trained_evaluations: list[dict[str, Any]],
    gate: dict[str, Any],
) -> dict[str, Any]:
    base = {row["case_id"]: row for row in base_evaluations}
    trained = {row["case_id"]: row for row in trained_evaluations}
    if set(base) != set(trained) or len(base) != len(base_evaluations) or len(trained) != len(trained_evaluations):
        raise ValueError("base and trained paired cases differ")
    metrics = {}
    for metric in ("program_exact", "executed_state_exact", "decision_correct", "accepted_by_verifier"):
        pairs = [(base[case_id][metric], trained[case_id][metric]) for case_id in sorted(base)]
        improved = sum(not before and after for before, after in pairs)
        degraded = sum(before and not after for before, after in pairs)
        base_correct = sum(before for before, _ in pairs)
        trained_correct = sum(after for _, after in pairs)
        metrics[metric] = {
            "base_correct": base_correct,
            "trained_correct": trained_correct,
            "base_rate": base_correct / len(pairs),
            "trained_rate": trained_correct / len(pairs),
            "delta": (trained_correct - base_correct) / len(pairs),
            "paired_improvements": improved,
            "paired_degradations": degraded,
            "one_sided_mcnemar_p": _one_sided_mcnemar_p(improved, degraded),
        }
    base_unsafe = sum(row["unsafe_authorization"] for row in base.values())
    trained_unsafe = sum(row["unsafe_authorization"] for row in trained.values())
    checks = {
        "program_exact_delta": metrics["program_exact"]["delta"] >= float(gate["program_exact_delta_floor"]),
        "executed_state_delta": metrics["executed_state_exact"]["delta"] >= float(gate["executed_state_delta_floor"]),
        "decision_delta": metrics["decision_correct"]["delta"] >= float(gate["decision_delta_floor"]),
        "verifier_acceptance_delta": metrics["accepted_by_verifier"]["delta"] >= float(gate["verifier_acceptance_delta_floor"]),
        "program_exact_paired_significance": (
            metrics["program_exact"]["one_sided_mcnemar_p"]
            <= float(gate["program_exact_mcnemar_p_ceiling"])
        ),
        "unsafe_authorizations_not_increased": (
            trained_unsafe - base_unsafe <= int(gate["unsafe_authorization_delta_ceiling"])
        ),
    }
    return {
        "paired_cases": len(base),
        "metrics": metrics,
        "base_unsafe_authorizations": base_unsafe,
        "trained_unsafe_authorizations": trained_unsafe,
        "unsafe_authorization_delta": trained_unsafe - base_unsafe,
        "checks": checks,
        "checks_passed": sum(checks.values()),
        "check_count": len(checks),
        "improvement_gate_passed": all(checks.values()),
    }