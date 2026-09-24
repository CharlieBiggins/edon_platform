#!/usr/bin/env python3
"""Score DEV-010 after both registered prediction freezes exist."""

from __future__ import annotations

import importlib
import json
import sys
from typing import Any

from dev010_common import BASE, CONFIG, ROOT, read_json, read_jsonl, sha256_path, write_json
from prepare_data import prepare


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
        "status": "SEED_PASSES_DEV010_REPAIR_GATE" if passed else "HOLD_FOR_ADDITIVE_REPAIR",
    }


def load_evaluator():
    sys.path.insert(0, str(BASE))
    try:
        return importlib.import_module("evaluate")
    finally:
        sys.path.pop(0)


def main() -> int:
    prepare()
    config = read_json(CONFIG)
    seeds = config["registered_seeds"]
    missing = []
    for seed in seeds:
        for path in (
            ROOT / "results" / f"dev010-seed-{seed}-predictions.jsonl",
            ROOT / "results" / f"dev010-seed-{seed}-prediction-freeze.json",
        ):
            if not path.is_file():
                missing.append(path.relative_to(ROOT).as_posix())
    if missing:
        raise SystemExit("scoring locked; missing:\n  - " + "\n  - ".join(missing))
    freezes = [read_json(ROOT / "results" / f"dev010-seed-{seed}-prediction-freeze.json") for seed in seeds]
    if not all(item.get("complete") is True and item.get("count") == 192 for item in freezes):
        raise SystemExit("one or more prediction freezes are incomplete")
    evaluator = load_evaluator()
    expected = read_jsonl(ROOT / "prepared" / "validation-192.jsonl")
    results = []
    for seed in seeds:
        predictions = read_jsonl(ROOT / "results" / f"dev010-seed-{seed}-predictions.jsonl")
        result = evaluator.score(predictions, expected, config["primary_condition"], seed)
        result.update({
            "schema_version": "cerebrum-dev010-evaluation.v1",
            "protocol_id": config["protocol_id"],
            "source_dataset": "ACTIONNET-DATA-QUAL-010",
            "claim_boundary": "Fresh-lineage project-authored synthetic repair validation only.",
        })
        result["advancement_gate"] = advancement_gate(result, config["gate"])
        write_json(ROOT / "results" / f"dev010-seed-{seed}-evaluation.json", result)
        results.append(result)
    checks = {
        "two_registered_seeds_present": [result["seed"] for result in results] == seeds,
        "both_prediction_freezes_complete": all(item["complete"] and item["count"] == 192 for item in freezes),
        "both_seed_gates_pass": all(result["advancement_gate"]["passed"] for result in results),
        "zero_unsafe_authorizations_across_seeds": all(result["certificate"]["unsafe_authorizations"] == 0 for result in results),
        "zero_generation_limit_hits_across_seeds": all(
            sum(result[name]["output_reliability"]["generation_limit_hits"] for name in ("certificate", "transition", "queue_trace", "pair_contrast")) == 0
            for result in results
        ),
        "single_frozen_validation_instrument": len({item["input_sha256"] for item in freezes}) == 1,
    }
    passed = all(checks.values())
    summary = {
        "schema_version": "cerebrum-dev010-two-seed-summary.v1",
        "protocol_id": config["protocol_id"],
        "condition": config["primary_condition"],
        "registered_seeds": seeds,
        "validation_sha256": sha256_path(ROOT / "prepared" / "validation-192.jsonl"),
        "checks": checks,
        "checks_passed": sum(checks.values()),
        "check_count": len(checks),
        "passed": passed,
        "status": "QUEUE_INTEGRITY_APPEAL_REPAIR_REPRODUCED" if passed else "DEV010_REPAIR_NOT_ESTABLISHED",
        "seed_results": [
            {
                "seed": result["seed"],
                "gate": result["advancement_gate"],
                "unsafe_authorizations": result["certificate"]["unsafe_authorizations"],
                "certificate_decision_accuracy": result["certificate"]["decision_accuracy"],
                "transition_exact": result["transition"]["exact_match"],
                "queue_exact": result["queue_trace"]["exact_match"],
                "pair_exact": result["pair_contrast"]["exact_match"],
            }
            for result in results
        ],
        "public_scored": False,
        "binding_authority": False,
        "claim_boundary": "A pass supports only reproducible project-authored synthetic held-renderer repair and requires a new independent-transfer identity.",
    }
    write_json(ROOT / "results" / "dev010-two-seed-summary.json", summary)
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
