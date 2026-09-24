#!/usr/bin/env python3
"""Write a compact field-level audit of the frozen DEV-014 errors."""

from __future__ import annotations

import importlib
import json
import sys
from collections import Counter
from typing import Any

from dev014_common import BASE, ROOT, read_jsonl, write_json
from prepare_data import prepare


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
        if expected == actual:
            return []
        return [prefix or "$"]
    return [] if expected == actual else [prefix or "$"]


def main() -> int:
    prepare()
    predictions_path = ROOT / "results" / "dev014-full-predictions.jsonl"
    if not predictions_path.is_file():
        raise SystemExit("DEV-014 predictions are not present")
    sys.path.insert(0, str(BASE))
    try:
        evaluator = importlib.import_module("evaluate")
    finally:
        sys.path.pop(0)
    expected = read_jsonl(ROOT / "prepared" / "full-regression-192.jsonl")
    predicted = {row["case_id"]: row for row in read_jsonl(predictions_path)}
    failures = []
    path_counts: Counter[str] = Counter()
    task_counts: Counter[str] = Counter()
    for row in expected:
        prediction = predicted[row["case_id"]]
        target = evaluator.expected_compiled(row)
        actual = evaluator.compiled_prediction(row, prediction)
        paths = differing_paths(target, actual)
        if not paths and not prediction.get("hit_generation_limit"):
            continue
        task = row["task_type"]
        task_counts[task] += 1
        path_counts.update(f"{task}:{path}" for path in paths)
        failures.append({
            "case_id": row["case_id"],
            "task_type": task,
            "pair_class": row["pair_class"],
            "intervention_family": row.get("intervention_family"),
            "pair_mechanism": row.get("pair_mechanism"),
            "differing_paths": paths,
            "hit_generation_limit": prediction.get("hit_generation_limit") is True,
        })
    result = {
        "schema_version": "cerebrum-dev014-error-audit.v1",
        "protocol_id": "CEREBRUM-DEV-014-FULL",
        "failure_count": len(failures),
        "failures_by_task": dict(sorted(task_counts.items())),
        "most_common_differing_paths": [
            {"path": path, "count": count} for path, count in path_counts.most_common(30)
        ],
        "failures": failures,
        "binding_authority": False,
    }
    output = ROOT / "results" / "dev014-error-audit.json"
    write_json(output, result)
    print(json.dumps({
        "failure_count": result["failure_count"],
        "failures_by_task": result["failures_by_task"],
        "saved": str(output),
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())