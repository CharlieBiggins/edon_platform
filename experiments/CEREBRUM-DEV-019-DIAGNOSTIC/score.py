#!/usr/bin/env python3
"""Score the frozen repeated-measures diagnostic without selecting a model."""

from __future__ import annotations

import json

from dev019_common import CONFIG, ROOT, read_json, read_jsonl, sha256_path, write_json
from diagnostic_analysis import analyze_predictions
from prepare_data import prepare


def main() -> int:
    prepare()
    config = read_json(CONFIG)
    freeze_path = ROOT / "results" / "diagnostic-prediction-freeze.json"
    if not freeze_path.is_file():
        raise SystemExit("diagnostic scoring locked until prediction freeze exists")
    freeze = read_json(freeze_path)
    if freeze.get("complete") is not True or freeze.get("count") != config["registered_predictions"]:
        raise SystemExit("diagnostic prediction freeze is incomplete")
    expected_path = ROOT / "prepared" / "diagnostic-matrix-160.jsonl"
    predictions_path = ROOT / "results" / "diagnostic-predictions.jsonl"
    if freeze["input_sha256"] != sha256_path(expected_path):
        raise SystemExit("diagnostic input changed after prediction")
    if freeze["predictions_sha256"] != sha256_path(predictions_path):
        raise SystemExit("diagnostic predictions changed after freeze")
    analysis = analyze_predictions(
        read_jsonl(expected_path),
        read_jsonl(predictions_path),
        config["diagnostic_conditions"],
    )
    controls = {
        "registered_prediction_count_160": freeze["count"] == 160,
        "registered_scenario_count_32": freeze["scenario_count"] == 32,
        "complete_repeated_measures": analysis["complete_repeated_measures"] is True,
        "all_conditions_reported": set(analysis["condition_results"]) == set(config["diagnostic_conditions"]),
        "no_training_performed": config["training_steps"] == 0,
        "deterministic_decoding": freeze["deterministic_decoding"] is True,
        "no_confirmation_or_selection": freeze["confirmation"] is False,
    }
    result = {
        "schema_version": "cerebrum-dev019-diagnostic-result.v1",
        "protocol_id": config["protocol_id"],
        "status": "DIAGNOSTIC_LOCALIZATION_COMPLETE" if all(controls.values()) else "DIAGNOSTIC_LOCALIZATION_INVALID",
        "passed": all(controls.values()),
        "controls": controls,
        "controls_passed": sum(controls.values()),
        "control_count": len(controls),
        "prediction_freeze_sha256": sha256_path(freeze_path),
        "analysis": analysis,
        "earliest_supported_failure_stage": analysis["dominant_decision_recovery"],
        "training_steps": 0,
        "confirmation_scored": False,
        "transfer_authorized": False,
        "binding_authority": False,
        "claim_boundary": "Cumulative gold interventions identify an earliest demonstrated recovery stage under this fresh synthetic instrument. They do not establish a unique causal defect, learned repair, independent transfer, production authority, or IGI.",
    }
    write_json(ROOT / "results" / "dev019-diagnostic-result.json", result)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())