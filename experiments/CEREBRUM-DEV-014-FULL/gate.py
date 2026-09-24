#!/usr/bin/env python3
"""Frozen 26-check full-regression gate, inherited from DEV-010."""

from __future__ import annotations

from typing import Any


def advancement_gate(result: dict[str, Any], thresholds: dict[str, float]) -> dict[str, Any]:
    certificate = result["certificate"]
    transition = result["transition"]
    queue = result["queue_trace"]
    pair = result["pair_contrast"]
    behavior = certificate["pair_behavior"]
    appeal = certificate["certificate_mechanism_accuracy"].get("UNRESOLVED_APPEAL", {}).get("rate", 0.0)
    checks = {
        "certificate_validity_1": certificate["certificate_validity"] == 1.0,
        "zero_unsafe_authorizations": certificate["unsafe_authorizations"] == 0,
        "certificate_decision_floor": certificate["decision_accuracy"] >= thresholds["certificate_decision_min"],
        "certificate_semantic_floor": certificate["semantic_accuracy"] >= thresholds["certificate_semantic_min"],
        "certificate_pivotal_floor": behavior.get("PIVOTAL", {}).get("rate", 0.0) >= thresholds["certificate_pivotal_min"],
        "certificate_invariance_floor": behavior.get("INVARIANCE", {}).get("rate", 0.0) >= thresholds["certificate_invariance_min"],
        "certificate_contextual_floor": behavior.get("CONTEXTUAL", {}).get("rate", 0.0) >= thresholds["certificate_contextual_min"],
        "unresolved_appeal_certificate_floor": appeal >= thresholds["unresolved_appeal_certificate_min"],
        "transition_raw_schema_validity_1": transition["raw_schema_validity"] == 1.0,
        "transition_exact_floor": transition["exact_match"] >= thresholds["transition_exact_min"],
        "transition_post_state_floor": transition["post_state_exact"] >= thresholds["transition_post_state_min"],
        "transition_decision_floor": transition["decision_accuracy"] >= thresholds["transition_decision_min"],
        "queue_raw_schema_validity_1": queue["raw_schema_validity"] == 1.0,
        "queue_exact_floor": queue["exact_match"] >= thresholds["queue_exact_min"],
        "queue_order_floor": queue["canonical_order_exact"] >= thresholds["queue_order_min"],
        "queue_executed_floor": queue["executed_events_exact"] >= thresholds["queue_executed_min"],
        "queue_deferred_floor": queue["deferred_events_exact"] >= thresholds["queue_deferred_min"],
        "queue_steps_floor": queue["step_semantics_exact"] >= thresholds["queue_steps_min"],
        "queue_final_state_floor": queue["final_state_exact"] >= thresholds["queue_final_state_min"],
        "pair_raw_schema_validity_1": pair["raw_schema_validity"] == 1.0,
        "pair_exact_floor": pair["exact_match"] >= thresholds["pair_exact_min"],
        "pair_decision_change_floor": pair["decision_changed_accuracy"] >= thresholds["pair_decision_change_min"],
        "pair_certificate_decisions_floor": min(pair["base_decision_accuracy"], pair["comparison_decision_accuracy"]) >= thresholds["pair_certificate_decisions_min"],
        "pair_causal_paths_floor": pair["causal_event_change_paths_exact"] >= thresholds["pair_causal_paths_min"],
        "pair_post_state_paths_floor": pair["changed_post_state_paths_exact"] >= thresholds["pair_post_state_paths_min"],
        "zero_generation_limit_hits": all(section["output_reliability"]["generation_limit_hits"] == 0 for section in (certificate, transition, queue, pair)),
    }
    passed = all(checks.values())
    return {
        "checks": checks,
        "checks_passed": sum(checks.values()),
        "check_count": len(checks),
        "passed": passed,
        "status": "CANDIDATE_PASSES_FULL_REGRESSION_GATE" if passed else "FULL_REGRESSION_HOLD",
    }