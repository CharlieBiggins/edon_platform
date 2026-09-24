#!/usr/bin/env python3
"""Select at most one representation without accessing heldout predictions."""

from __future__ import annotations

import json

from dev020_common import CONFIG, ROOT, read_json, read_jsonl, sha256_path, write_json
from interface_analysis import analyze
from prepare_data import prepare_calibration


def main() -> int:
    prepare_calibration()
    config = read_json(CONFIG)
    freeze_path = ROOT / "results" / "calibration-prediction-freeze.json"
    if not freeze_path.is_file():
        raise SystemExit("calibration scoring locked until prediction freeze exists")
    freeze = read_json(freeze_path)
    expected_path = ROOT / "prepared" / "format-calibration-384.jsonl"
    predictions_path = ROOT / "results" / "calibration-predictions.jsonl"
    if freeze.get("complete") is not True or freeze.get("count") != config["registered_calibration_predictions"]:
        raise SystemExit("calibration prediction freeze is incomplete")
    if freeze["input_sha256"] != sha256_path(expected_path):
        raise SystemExit("calibration input changed after prediction")
    if freeze["predictions_sha256"] != sha256_path(predictions_path):
        raise SystemExit("calibration predictions changed after freeze")
    analysis = analyze(
        read_jsonl(expected_path),
        read_jsonl(predictions_path),
        config["baseline_representation"],
        config["candidate_representations"],
        config["fidelity_condition"],
        config["selection_gates"],
        config["fidelity_gates"],
    )
    selected = analysis["selected_representation"]
    controls = {
        "registered_prediction_count_384": freeze["count"] == 384,
        "registered_scenario_count_64": freeze["scenario_count"] == 64,
        "complete_analysis": analysis["complete"] is True,
        "all_candidates_reported": set(analysis["representation_comparisons"]) == set(config["candidate_representations"]),
        "fidelity_condition_reported": config["fidelity_condition"] in analysis["condition_results"],
        "deterministic_decoding": freeze["deterministic_decoding"] is True,
        "heldout_not_accessed": freeze["heldout_validation_accessed"] is False,
        "no_training_performed": config["training_steps"] == 0,
    }
    selection_freeze = {
        "schema_version": "cerebrum-dev020-representation-selection-freeze.v1",
        "protocol_id": config["protocol_id"],
        "selected_representation": selected,
        "representation_qualified": selected is not None,
        "qualifying_representations": analysis["qualifying_representations"],
        "fidelity_passed_calibration": analysis["fidelity_passed"],
        "calibration_input_sha256": sha256_path(expected_path),
        "calibration_predictions_sha256": sha256_path(predictions_path),
        "calibration_prediction_freeze_sha256": sha256_path(freeze_path),
        "selection_gates": config["selection_gates"],
        "selection_tie_breaker": config["selection_tie_breaker"],
        "fidelity_gates": config["fidelity_gates"],
        "heldout_validation_accessed": False,
        "training_steps": 0,
        "transfer_authorized": False,
        "binding_authority": False,
    }
    selection_path = ROOT / "results" / "representation-selection-freeze.json"
    write_json(selection_path, selection_freeze)
    result = {
        "schema_version": "cerebrum-dev020-calibration-result.v1",
        "protocol_id": config["protocol_id"],
        "status": "REPRESENTATION_SELECTED_FOR_HELDOUT_VALIDATION" if selected else "INTERFACE_CALIBRATION_HOLD",
        "passed": all(controls.values()),
        "representation_qualified": selected is not None,
        "selected_representation": selected,
        "fidelity_passed": analysis["fidelity_passed"],
        "controls": controls,
        "controls_passed": sum(controls.values()),
        "control_count": len(controls),
        "analysis": analysis,
        "prediction_freeze_sha256": sha256_path(freeze_path),
        "selection_freeze_sha256": sha256_path(selection_path),
        "heldout_validation_accessed": False,
        "training_steps": 0,
        "transfer_authorized": False,
        "binding_authority": False,
        "claim_boundary": (
            "Development-only frozen-model interface calibration. Selection does not establish learned repair, "
            "transfer, production authority, or IGI."
        ),
    }
    write_json(ROOT / "results" / "dev020-calibration-result.json", result)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())