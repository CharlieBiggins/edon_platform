#!/usr/bin/env python3
"""Audit the frozen DEV-015 development errors before DEV-016 execution."""

from __future__ import annotations

import importlib
import json
import sys
from collections import Counter
from typing import Any

from dev016_common import BASE, PARENT, ROOT, read_jsonl, sha256_path, write_json


def differing_paths(expected: Any, actual: Any, prefix: str = "") -> list[str]:
    if type(expected) is not type(actual):
        return [prefix or "$"]
    if isinstance(expected, dict):
        paths: list[str] = []
        for key in sorted(set(expected) | set(actual)):
            path = f"{prefix}.{key}" if prefix else key
            if key not in expected or key not in actual:
                paths.append(path)
            else:
                paths.extend(differing_paths(expected[key], actual[key], path))
        return paths
    if isinstance(expected, list):
        return [] if expected == actual else [prefix or "$"]
    return [] if expected == actual else [prefix or "$"]


def main() -> int:
    expected_path = PARENT / "prepared" / "development-selection-64.jsonl"
    prediction_paths = {
        "continuation-step-12": PARENT / "results" / "development-continuation-step-12-predictions.jsonl",
        "continuation-step-24": PARENT / "results" / "development-continuation-step-24-predictions.jsonl",
    }
    if not expected_path.is_file() or not all(path.is_file() for path in prediction_paths.values()):
        raise SystemExit("frozen DEV-015 development inputs or predictions are not present for audit")
    sys.path.insert(0, str(BASE))
    try:
        evaluator = importlib.import_module("evaluate")
    finally:
        sys.path.pop(0)
    expected = read_jsonl(expected_path)
    expected_by_case = {row["case_id"]: row for row in expected}
    candidate_reports: dict[str, Any] = {}
    compiled_by_candidate: dict[str, dict[str, Any]] = {}
    for candidate_id, path in prediction_paths.items():
        predictions = {row["case_id"]: row for row in read_jsonl(path)}
        failures = []
        paths: Counter[str] = Counter()
        tasks: Counter[str] = Counter()
        compiled_by_case: dict[str, Any] = {}
        for case_id, row in expected_by_case.items():
            prediction = predictions[case_id]
            target = evaluator.expected_compiled(row)
            actual = evaluator.compiled_prediction(row, prediction)
            compiled_by_case[case_id] = actual
            differences = differing_paths(target, actual)
            if not differences and prediction.get("hit_generation_limit") is not True:
                continue
            task = row["task_type"]
            tasks[task] += 1
            paths.update(f"{task}:{item}" for item in differences)
            expected_decision = target.get("decision") if isinstance(target, dict) else None
            actual_decision = actual.get("decision") if isinstance(actual, dict) else None
            failures.append({
                "case_id": case_id,
                "task_type": task,
                "pair_class": row["pair_class"],
                "variant": row["variant"],
                "intervention_family": row.get("intervention_family"),
                "pair_mechanism": row.get("pair_mechanism"),
                "expected_decision": expected_decision,
                "actual_decision": actual_decision,
                "unsafe_authorization": (
                    task == "CERTIFICATE"
                    and expected_decision != "ALLOW"
                    and actual_decision == "ALLOW"
                ),
                "differing_paths": differences,
                "hit_generation_limit": prediction.get("hit_generation_limit") is True,
            })
        compiled_by_candidate[candidate_id] = compiled_by_case
        candidate_reports[candidate_id] = {
            "predictions_sha256": sha256_path(path),
            "failure_count": len(failures),
            "failures_by_task": dict(sorted(tasks.items())),
            "most_common_differing_paths": [
                {"path": item, "count": count} for item, count in paths.most_common(30)
            ],
            "unsafe_authorizations": [row for row in failures if row["unsafe_authorization"]],
            "failures": failures,
        }
    step12 = compiled_by_candidate["continuation-step-12"]
    step24 = compiled_by_candidate["continuation-step-24"]
    changed_cases = sorted(case_id for case_id in step12 if step12[case_id] != step24[case_id])
    result = {
        "schema_version": "cerebrum-dev016-parent-error-audit.v1",
        "protocol_id": "CEREBRUM-DEV-016-NARROW",
        "parent_protocol": "CEREBRUM-DEV-015-MIXED",
        "development_input_sha256": sha256_path(expected_path),
        "candidate_reports": candidate_reports,
        "compiled_outputs_identical_between_parent_checkpoints": not changed_cases,
        "compiled_output_changed_case_ids": changed_cases,
        "selected_repair_parent": "continuation-step-12",
        "confirmation_accessed": False,
        "binding_authority": False,
    }
    output = ROOT / "results" / "parent-dev015-error-audit.json"
    write_json(output, result)
    print(json.dumps({
        "saved": str(output),
        "step12_failures": candidate_reports["continuation-step-12"]["failure_count"],
        "step24_failures": candidate_reports["continuation-step-24"]["failure_count"],
        "compiled_outputs_identical": not changed_cases,
        "confirmation_accessed": False,
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())