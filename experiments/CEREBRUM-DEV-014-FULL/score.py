#!/usr/bin/env python3
"""Score the frozen DEV-014 full multi-task regression."""

from __future__ import annotations

import importlib
import json
import sys

from dev014_common import BASE, CONFIG, ROOT, read_json, read_jsonl, sha256_path, write_json
from gate import advancement_gate
from prepare_data import prepare


def load_evaluator():
    sys.path.insert(0, str(BASE))
    try:
        return importlib.import_module("evaluate")
    finally:
        sys.path.pop(0)


def main() -> int:
    prepare()
    config = read_json(CONFIG)
    freeze_path = ROOT / "results" / "dev014-full-prediction-freeze.json"
    if not freeze_path.is_file():
        raise SystemExit("scoring locked until the full-regression prediction freeze exists")
    freeze = read_json(freeze_path)
    if freeze.get("complete") is not True or freeze.get("count") != 192:
        raise SystemExit("full-regression prediction freeze is incomplete")
    expected_path = ROOT / "prepared" / "full-regression-192.jsonl"
    predictions_path = ROOT / "results" / "dev014-full-predictions.jsonl"
    if freeze.get("input_sha256") != sha256_path(expected_path):
        raise SystemExit("full-regression input changed after prediction freeze")
    if freeze.get("predictions_sha256") != sha256_path(predictions_path):
        raise SystemExit("full-regression predictions changed after freeze")
    evaluator = load_evaluator()
    result = evaluator.score(
        read_jsonl(predictions_path),
        read_jsonl(expected_path),
        config["primary_condition"],
        config["parent_continuation_seed"],
    )
    gate = advancement_gate(result, config["gate"])
    passed = gate["passed"]
    result.update({
        "schema_version": "cerebrum-dev014-full-result.v1",
        "protocol_id": config["protocol_id"],
        "source_dataset": config["source_dataset"],
        "selected_candidate_id": config["selected_candidate_id"],
        "selected_step": config["selected_step"],
        "full_regression_gate": gate,
        "passed": passed,
        "status": "FULL_MULTITASK_REGRESSION_SIGNAL" if passed else "FULL_MULTITASK_REGRESSION_HOLD",
        "next_gate": "fresh-seed candidate reproduction before any independent-transfer identity" if passed else "audit failures before further adaptation",
        "full_regression": True,
        "seed_reproducibility_established": False,
        "transfer_authorized": False,
        "public_scored": False,
        "binding_authority": False,
        "claim_boundary": "One frozen candidate on one fresh project-authored synthetic full regression; no seed reproducibility, independent transfer, real-institution, production, authority, or IGI claim.",
    })
    write_json(ROOT / "results" / "dev014-full-result.json", result)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())