#!/usr/bin/env python3
"""Score the single registered DEV-012 balance continuation."""

from __future__ import annotations

import importlib.util
import json
import sys

from dev012_common import CONFIG, PARENT, ROOT, read_json, read_jsonl, sha256_path, write_json
from prepare_data import prepare


def load_parent_scorer():
    path = PARENT / "score.py"
    spec = importlib.util.spec_from_file_location("dev011_score_for_dev012", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load parent scorer: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(PARENT))
    try:
        spec.loader.exec_module(module)
        return module
    finally:
        sys.path.pop(0)


def main() -> int:
    prepare()
    config = read_json(CONFIG)
    seed = int(config["continuation_seed"])
    predictions_path = ROOT / "results" / f"dev012-seed-{seed}-predictions.jsonl"
    freeze_path = ROOT / "results" / f"dev012-seed-{seed}-prediction-freeze.json"
    if not predictions_path.is_file() or not freeze_path.is_file():
        raise SystemExit("DEV-012 scoring locked until the prediction freeze exists")
    freeze = read_json(freeze_path)
    if freeze.get("complete") is not True or freeze.get("count") != 64:
        raise SystemExit("DEV-012 prediction freeze is incomplete")
    expected = read_jsonl(ROOT / "prepared" / "focused-validation-64.jsonl")
    predictions = read_jsonl(predictions_path)
    parent_scorer = load_parent_scorer()
    metrics = parent_scorer.score_seed(expected, predictions, parent_scorer.load_evaluator(), config)
    passed = metrics["focused_gate"]["passed"]
    result = {
        "schema_version": "cerebrum-dev012-focused-result.v1",
        "protocol_id": config["protocol_id"],
        "continuation_seed": seed,
        "parent_continuation_seed": config["parent_continuation_seed"],
        "parent_dev010_seed": config["parent_dev010_seed"],
        "validation_sha256": sha256_path(ROOT / "prepared" / "focused-validation-64.jsonl"),
        "predictions_sha256": sha256_path(predictions_path),
        "metrics": metrics,
        "passed": passed,
        "status": "FOCUSED_BALANCE_REPAIR_SIGNAL" if passed else "FOCUSED_BALANCE_REPAIR_HOLD",
        "next_gate": "fresh full multi-task regression before any new transfer identity",
        "full_regression": False,
        "transfer_authorized": False,
        "public_scored": False,
        "binding_authority": False,
        "claim_boundary": (
            "A pass is only an adaptive synthetic focused balance-repair signal for one candidate. It does not "
            "establish seed reproducibility, full-task retention, or transfer."
        ),
    }
    write_json(ROOT / "results" / "dev012-focused-result.json", result)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())