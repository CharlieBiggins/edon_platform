#!/usr/bin/env python3
"""Select only a checkpoint that passes every frozen development check."""

from __future__ import annotations

import json
from typing import Any

from dev015_common import CONFIG, ROOT, candidate_specs, read_json, read_jsonl, sha256_path, sha256_tree, write_json
from prepare_data import prepare
from scoring import score_rows


def choose_candidate(rows: list[dict[str, Any]]) -> dict[str, Any] | None:
    eligible = [row for row in rows if row["eligible"]]
    if not eligible:
        return None
    return max(
        eligible,
        key=lambda row: (
            row["metrics"]["queue_trace"]["exact_match"],
            row["metrics"]["transition"]["exact_match"],
            row["metrics"]["certificate"]["decision_accuracy"],
            row["metrics"]["certificate"]["certificate_mechanism_accuracy"].get("UNRESOLVED_APPEAL", {}).get("rate", 0.0),
            row["metrics"]["pair_contrast"]["exact_match"],
            -int(row["step"]),
        ),
    )


def main() -> int:
    prepare()
    config = read_json(CONFIG)
    freeze_path = ROOT / "results" / "development-prediction-freeze.json"
    if not freeze_path.is_file():
        raise SystemExit("development selection locked until all checkpoint predictions are frozen")
    freeze = read_json(freeze_path)
    if freeze.get("all_complete") is not True:
        raise SystemExit("development checkpoint predictions are incomplete")
    selection_path = ROOT / "results" / "selected-candidate.json"
    if selection_path.is_file():
        existing = read_json(selection_path)
        if existing.get("development_prediction_freeze_sha256") != sha256_path(freeze_path):
            raise SystemExit("existing selection is bound to a different prediction freeze")
        print(json.dumps(existing, indent=2, sort_keys=True))
        return 0
    expected = read_jsonl(ROOT / "prepared" / "development-selection-64.jsonl")
    frozen = {item["candidate_id"]: item for item in freeze["candidates"]}
    rows = []
    for candidate in candidate_specs(config):
        record = frozen.get(candidate["candidate_id"])
        predictions_path = ROOT / "results" / f"development-{candidate['candidate_id']}-predictions.jsonl"
        if record is None:
            raise SystemExit(f"candidate absent from development freeze: {candidate['candidate_id']}")
        if sha256_path(predictions_path) != record["predictions_sha256"]:
            raise SystemExit(f"predictions changed after freeze: {candidate['candidate_id']}")
        if sha256_tree(candidate["adapter"]) != record["adapter_tree_sha256"]:
            raise SystemExit(f"adapter changed after prediction: {candidate['candidate_id']}")
        metrics = score_rows(expected, read_jsonl(predictions_path), config)
        rows.append({
            "candidate_id": candidate["candidate_id"],
            "step": candidate["step"],
            "adapter_tree_sha256": record["adapter_tree_sha256"],
            "predictions_sha256": record["predictions_sha256"],
            "eligible": metrics["full_regression_gate"]["passed"],
            "metrics": metrics,
        })
    selected = choose_candidate(rows)
    result = {
        "schema_version": "cerebrum-dev015-development-selection.v1",
        "protocol_id": config["protocol_id"],
        "development_input_sha256": sha256_path(ROOT / "prepared" / "development-selection-64.jsonl"),
        "development_prediction_freeze_sha256": sha256_path(freeze_path),
        "selection_rule": config["selection_ranking"],
        "candidate_results": rows,
        "selected_candidate_id": selected["candidate_id"] if selected else None,
        "selected_step": selected["step"] if selected else None,
        "selected_adapter_tree_sha256": selected["adapter_tree_sha256"] if selected else None,
        "status": "SAFE_FULL_DEVELOPMENT_CANDIDATE_SELECTED" if selected else "NO_DEVELOPMENT_CANDIDATE_PASSES_FULL_GATE",
        "confirmation_scored": False,
        "full_regression": False,
        "transfer_authorized": False,
        "binding_authority": False,
        "claim_boundary": "Adaptive checkpoint selection on fresh development data only; untouched confirmation remains sealed.",
    }
    write_json(selection_path, result)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())