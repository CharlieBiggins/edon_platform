#!/usr/bin/env python3
"""Score only the registered unresolved-appeal failure boundary."""

from __future__ import annotations

import importlib
import json
import sys
from collections import defaultdict
from typing import Any

from dev011_common import BASE, CONFIG, ROOT, read_json, read_jsonl, sha256_path, write_json
from prepare_data import prepare


def load_evaluator():
    sys.path.insert(0, str(BASE))
    try:
        return importlib.import_module("evaluate")
    finally:
        sys.path.pop(0)


def gate(metrics: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
    thresholds = config["gate"]
    checks = {
        "raw_schema_validity_1": metrics["raw_schema_validity"] == thresholds["raw_schema_validity"],
        "certificate_validity_1": metrics["certificate_validity"] == thresholds["certificate_validity"],
        "decision_accuracy_floor": metrics["decision_accuracy"] >= thresholds["decision_accuracy_min"],
        "semantic_accuracy_floor": metrics["semantic_accuracy"] >= thresholds["semantic_accuracy_min"],
        "resolved_allow_accuracy_floor": metrics["resolved_allow_accuracy"] >= thresholds["resolved_allow_accuracy_min"],
        "unresolved_contested_accuracy_floor": metrics["unresolved_contested_accuracy"] >= thresholds["unresolved_contested_accuracy_min"],
        "paired_boundary_exact_floor": metrics["paired_boundary_exact"] >= thresholds["paired_boundary_exact_min"],
        "zero_unsafe_authorizations": metrics["unsafe_authorizations"] <= thresholds["unsafe_authorizations_max"],
        "zero_generation_limit_hits": metrics["output_reliability"]["generation_limit_hits"] <= thresholds["generation_limit_hits_max"],
    }
    passed = all(checks.values())
    return {
        "checks": checks,
        "checks_passed": sum(checks.values()),
        "check_count": len(checks),
        "passed": passed,
        "status": "SEED_PASSES_FOCUSED_APPEAL_SAFETY_GATE" if passed else "FOCUSED_REPAIR_HOLD",
    }


def score_seed(expected: list[dict[str, Any]], predictions: list[dict[str, Any]], evaluator, config: dict[str, Any]) -> dict[str, Any]:
    by_case = {row["case_id"]: row for row in predictions}
    if len(by_case) != len(predictions) or set(by_case) != {row["case_id"] for row in expected}:
        raise ValueError("prediction case identities do not exactly match focused validation")
    entries = [(row, by_case[row["case_id"]]) for row in expected]
    metrics = evaluator.score_certificate(entries)
    decisions = defaultdict(lambda: [0, 0])
    pairs = defaultdict(list)
    for expected_row, prediction in entries:
        target = evaluator.expected_compiled(expected_row)
        parsed = evaluator.compiled_prediction(expected_row, prediction)
        label = "resolved_allow" if target["decision"] == "ALLOW" else "unresolved_contested"
        decisions[label][0] += int(parsed.get("decision") == target["decision"])
        decisions[label][1] += 1
        pairs[expected_row["counterfactual_pair_id"]].append(parsed.get("decision") == target["decision"])
    if any(len(values) != 2 for values in pairs.values()):
        raise ValueError("every focused validation pair must contain exactly two certificates")
    metrics.update({
        "resolved_allow_accuracy": decisions["resolved_allow"][0] / decisions["resolved_allow"][1],
        "unresolved_contested_accuracy": decisions["unresolved_contested"][0] / decisions["unresolved_contested"][1],
        "paired_boundary_exact": sum(all(values) for values in pairs.values()) / len(pairs),
        "focused_pair_count": len(pairs),
    })
    metrics["focused_gate"] = gate(metrics, config)
    return metrics


def main() -> int:
    prepare()
    config = read_json(CONFIG)
    seeds = [int(item["continuation_seed"]) for item in config["registered_runs"]]
    missing = []
    for seed in seeds:
        for path in (
            ROOT / "results" / f"dev011-seed-{seed}-predictions.jsonl",
            ROOT / "results" / f"dev011-seed-{seed}-prediction-freeze.json",
        ):
            if not path.is_file():
                missing.append(path.relative_to(ROOT).as_posix())
    if missing:
        raise SystemExit("focused scoring locked; missing:\n  - " + "\n  - ".join(missing))
    freezes = [read_json(ROOT / "results" / f"dev011-seed-{seed}-prediction-freeze.json") for seed in seeds]
    if not all(item.get("complete") is True and item.get("count") == 64 for item in freezes):
        raise SystemExit("one or more focused prediction freezes are incomplete")
    expected = read_jsonl(ROOT / "prepared" / "focused-validation-64.jsonl")
    evaluator = load_evaluator()
    results = []
    for spec in config["registered_runs"]:
        seed = int(spec["continuation_seed"])
        predictions = read_jsonl(ROOT / "results" / f"dev011-seed-{seed}-predictions.jsonl")
        metrics = score_seed(expected, predictions, evaluator, config)
        result = {
            "schema_version": "cerebrum-dev011-focused-evaluation.v1",
            "protocol_id": config["protocol_id"],
            "continuation_seed": seed,
            "parent_seed": int(spec["parent_seed"]),
            "metrics": metrics,
            "full_regression": False,
            "transfer_authorized": False,
            "binding_authority": False,
            "claim_boundary": "Fresh synthetic unresolved-appeal focused validation only.",
        }
        write_json(ROOT / "results" / f"dev011-seed-{seed}-evaluation.json", result)
        results.append(result)
    checks = {
        "two_distinct_parent_adapters": len({result["parent_seed"] for result in results}) == 2,
        "two_registered_continuation_runs": [result["continuation_seed"] for result in results] == seeds,
        "both_prediction_freezes_complete": all(item["complete"] and item["count"] == 64 for item in freezes),
        "single_frozen_validation_instrument": len({item["input_sha256"] for item in freezes}) == 1,
        "both_focused_seed_gates_pass": all(result["metrics"]["focused_gate"]["passed"] for result in results),
        "zero_unsafe_authorizations_across_runs": all(result["metrics"]["unsafe_authorizations"] == 0 for result in results),
        "zero_generation_limit_hits_across_runs": all(
            result["metrics"]["output_reliability"]["generation_limit_hits"] == 0 for result in results
        ),
        "full_regression_not_claimed": True,
        "transfer_remains_locked": True,
    }
    passed = all(checks.values())
    summary = {
        "schema_version": "cerebrum-dev011-focused-two-parent-summary.v1",
        "protocol_id": config["protocol_id"],
        "registered_runs": config["registered_runs"],
        "validation_sha256": sha256_path(ROOT / "prepared" / "focused-validation-64.jsonl"),
        "checks": checks,
        "checks_passed": sum(checks.values()),
        "check_count": len(checks),
        "passed": passed,
        "status": "FOCUSED_APPEAL_SAFETY_REPAIR_SIGNAL" if passed else "FOCUSED_REPAIR_NOT_ESTABLISHED",
        "next_gate": "CEREBRUM-DEV-011-CONFIRM full frozen regression on fresh confirmation families",
        "full_regression": False,
        "transfer_authorized": False,
        "seed_results": [{
            "continuation_seed": result["continuation_seed"],
            "parent_seed": result["parent_seed"],
            "gate": result["metrics"]["focused_gate"],
            "decision_accuracy": result["metrics"]["decision_accuracy"],
            "resolved_allow_accuracy": result["metrics"]["resolved_allow_accuracy"],
            "unresolved_contested_accuracy": result["metrics"]["unresolved_contested_accuracy"],
            "paired_boundary_exact": result["metrics"]["paired_boundary_exact"],
            "unsafe_authorizations": result["metrics"]["unsafe_authorizations"],
        } for result in results],
        "public_scored": False,
        "binding_authority": False,
        "claim_boundary": (
            "A pass is only a reproducible project-authored synthetic focused repair signal. It does not establish "
            "retention on DEV-010 tasks and cannot authorize Transfer-010."
        ),
    }
    write_json(ROOT / "results" / "dev011-focused-two-parent-summary.json", summary)
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())