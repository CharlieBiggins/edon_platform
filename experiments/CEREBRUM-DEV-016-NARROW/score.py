#!/usr/bin/env python3
"""Score the single-use 192-case DEV-016 confirmation."""

from __future__ import annotations

import json

from dev016_common import CONFIG, ROOT, read_json, read_jsonl, sha256_path, write_json
from prepare_data import prepare
from scoring import score_rows


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
            "schema_version": "cerebrum-dev016-narrow-result.v1",
            "protocol_id": config["protocol_id"],
            "passed": False,
            "status": "NO_DEVELOPMENT_CANDIDATE_PASSES_FULL_GATE",
            "selected_candidate_id": None,
            "confirmation_scored": False,
            "full_regression": False,
            "transfer_authorized": False,
            "binding_authority": False,
            "claim_boundary": "Development selection failed closed; untouched full confirmation was not exposed.",
        }
        write_json(ROOT / "results" / "dev016-narrow-result.json", result)
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0
    freeze_path = ROOT / "results" / "confirmation-prediction-freeze.json"
    if not freeze_path.is_file():
        raise SystemExit("confirmation scoring locked until its prediction freeze exists")
    freeze = read_json(freeze_path)
    if freeze.get("complete") is not True or freeze.get("count") != 192:
        raise SystemExit("confirmation prediction freeze is incomplete")
    if freeze.get("selection_sha256") != sha256_path(selection_path):
        raise SystemExit("confirmation freeze is not bound to the frozen selection")
    expected_path = ROOT / "prepared" / "untouched-confirmation-192.jsonl"
    predictions_path = ROOT / "results" / f"confirmation-{candidate_id}-predictions.jsonl"
    if freeze.get("input_sha256") != sha256_path(expected_path):
        raise SystemExit("confirmation input changed after prediction freeze")
    if freeze.get("predictions_sha256") != sha256_path(predictions_path):
        raise SystemExit("confirmation predictions changed after freeze")
    metrics = score_rows(read_jsonl(expected_path), read_jsonl(predictions_path), config)
    passed = metrics["full_regression_gate"]["passed"]
    result = {
        "schema_version": "cerebrum-dev016-narrow-result.v1",
        "protocol_id": config["protocol_id"],
        "continuation_seed": config["continuation_seed"],
        "selected_candidate_id": candidate_id,
        "selected_step": selection["selected_step"],
        "selection_sha256": sha256_path(selection_path),
        "confirmation_input_sha256": sha256_path(expected_path),
        "confirmation_predictions_sha256": sha256_path(predictions_path),
        "metrics": metrics,
        "passed": passed,
        "status": "NARROW_REPAIR_FULL_REGRESSION_SIGNAL" if passed else "NARROW_REPAIR_FULL_REGRESSION_HOLD",
        "next_gate": "fresh-seed reproduction before independent transfer" if passed else "freeze and audit without exposing confirmation cases to training",
        "confirmation_scored": True,
        "full_regression": True,
        "seed_reproducibility_established": False,
        "transfer_authorized": False,
        "public_scored": False,
        "binding_authority": False,
        "claim_boundary": "One adaptively selected narrow-repair candidate on one fresh project-authored synthetic full confirmation; no seed reproducibility, independent transfer, production, authority, or IGI claim.",
    }
    write_json(ROOT / "results" / "dev016-narrow-result.json", result)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())