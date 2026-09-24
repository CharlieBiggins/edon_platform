#!/usr/bin/env python3
"""Score the single untouched DEV-013 confirmation after candidate selection."""

from __future__ import annotations

import json

from dev013_common import CONFIG, ROOT, read_json, read_jsonl, sha256_path, write_json
from prepare_data import prepare
from scoring import load_scorer


def main() -> int:
    prepare()
    config = read_json(CONFIG)
    selection_path = ROOT / "results" / "selected-candidate.json"
    if not selection_path.is_file():
        raise SystemExit("scoring locked until development selection is frozen")
    selection = read_json(selection_path)
    candidate_id = selection.get("selected_candidate_id")
    if not candidate_id:
        result = {
            "schema_version": "cerebrum-dev013-focused-result.v1",
            "protocol_id": config["protocol_id"],
            "passed": False,
            "status": "NO_SAFE_DEVELOPMENT_CANDIDATE",
            "selected_candidate_id": None,
            "confirmation_scored": False,
            "full_regression": False,
            "transfer_authorized": False,
            "binding_authority": False,
            "claim_boundary": "Development selection failed closed; untouched confirmation was not exposed.",
        }
        write_json(ROOT / "results" / "dev013-focused-result.json", result)
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0
    freeze_path = ROOT / "results" / "confirmation-prediction-freeze.json"
    if not freeze_path.is_file():
        raise SystemExit("confirmation scoring locked until its prediction freeze exists")
    freeze = read_json(freeze_path)
    if freeze.get("complete") is not True or freeze.get("count") != 64:
        raise SystemExit("confirmation prediction freeze is incomplete")
    if freeze.get("selection_sha256") != sha256_path(selection_path):
        raise SystemExit("confirmation freeze is not bound to the frozen selection")
    expected = read_jsonl(ROOT / "prepared" / "untouched-confirmation-64.jsonl")
    predictions_path = ROOT / "results" / f"confirmation-{candidate_id}-predictions.jsonl"
    if freeze.get("input_sha256") != sha256_path(ROOT / "prepared" / "untouched-confirmation-64.jsonl"):
        raise SystemExit("confirmation input changed after prediction freeze")
    if freeze.get("predictions_sha256") != sha256_path(predictions_path):
        raise SystemExit("confirmation predictions changed after freeze")
    if freeze.get("selected_candidate_id") != candidate_id:
        raise SystemExit("confirmation candidate does not match frozen selection")
    scorer = load_scorer()
    metrics = scorer.score_seed(expected, read_jsonl(predictions_path), scorer.load_evaluator(), config)
    passed = metrics["focused_gate"]["passed"]
    result = {
        "schema_version": "cerebrum-dev013-focused-result.v1",
        "protocol_id": config["protocol_id"],
        "continuation_seed": config["continuation_seed"],
        "selected_candidate_id": candidate_id,
        "selected_step": selection["selected_step"],
        "selection_sha256": sha256_path(selection_path),
        "confirmation_input_sha256": sha256_path(ROOT / "prepared" / "untouched-confirmation-64.jsonl"),
        "confirmation_predictions_sha256": sha256_path(predictions_path),
        "metrics": metrics,
        "passed": passed,
        "status": "FOCUSED_NEAR_CLOCK_REPAIR_SIGNAL" if passed else "FOCUSED_NEAR_CLOCK_REPAIR_HOLD",
        "next_gate": "fresh full multi-task regression before any new transfer identity",
        "confirmation_scored": True,
        "full_regression": False,
        "transfer_authorized": False,
        "public_scored": False,
        "binding_authority": False,
        "claim_boundary": (
            "A pass is one safety-constrained synthetic near-clock confirmation signal after adaptive development "
            "selection. It does not establish seed reproducibility, full-task retention, or transfer."
        ),
    }
    write_json(ROOT / "results" / "dev013-focused-result.json", result)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())