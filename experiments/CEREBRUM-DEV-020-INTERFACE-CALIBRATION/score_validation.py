#!/usr/bin/env python3
"""Score the selected representation and decision fidelity on heldout cases."""

from __future__ import annotations

import json

from dev020_common import CONFIG, ROOT, read_json, read_jsonl, sha256_path, write_json
from interface_analysis import analyze
from prepare_data import prepare_validation


def main() -> int:
    config = read_json(CONFIG)
    selection_path = ROOT / "results" / "representation-selection-freeze.json"
    selection = read_json(selection_path)
    selected = selection.get("selected_representation")
    if not selected:
        raise SystemExit("no representation selected")
    prepare_validation(selected)
    calibration_result = read_json(ROOT / "results" / "dev020-calibration-result.json")
    freeze_path = ROOT / "results" / "validation-prediction-freeze.json"
    freeze = read_json(freeze_path)
    expected_path = ROOT / "prepared" / "heldout-selected-validation-192.jsonl"
    predictions_path = ROOT / "results" / "validation-predictions.jsonl"
    if freeze.get("complete") is not True or freeze.get("count") != config["registered_heldout_predictions_after_selection"]:
        raise SystemExit("heldout validation prediction freeze is incomplete")
    if freeze["selection_freeze_sha256"] != sha256_path(selection_path):
        raise SystemExit("representation selection changed after heldout access")
    if freeze["input_sha256"] != sha256_path(expected_path):
        raise SystemExit("heldout validation input changed after prediction")
    if freeze["predictions_sha256"] != sha256_path(predictions_path):
        raise SystemExit("heldout validation predictions changed after freeze")
    analysis = analyze(
        read_jsonl(expected_path),
        read_jsonl(predictions_path),
        config["baseline_representation"],
        [selected],
        config["fidelity_condition"],
        config["selection_gates"],
        config["fidelity_gates"],
    )
    representation_validated = analysis["representation_comparisons"][selected]["qualified"]
    fidelity_validated = analysis["fidelity_passed"]
    overall = (
        calibration_result.get("representation_qualified") is True
        and calibration_result.get("fidelity_passed") is True
        and representation_validated
        and fidelity_validated
    )
    controls = {
        "registered_prediction_count_192": freeze["count"] == 192,
        "registered_scenario_count_64": freeze["scenario_count"] == 64,
        "selected_representation_unchanged": freeze["selected_representation"] == selected,
        "complete_analysis": analysis["complete"] is True,
        "only_registered_conditions_scored": set(analysis["condition_results"]) == {
            config["baseline_representation"], selected, config["fidelity_condition"]
        },
        "deterministic_decoding": freeze["deterministic_decoding"] is True,
        "no_training_performed": config["training_steps"] == 0,
    }
    result = {
        "schema_version": "cerebrum-dev020-interface-result.v1",
        "protocol_id": config["protocol_id"],
        "status": "INTERFACE_CALIBRATION_SIGNAL" if overall and all(controls.values()) else "INTERFACE_CALIBRATION_HOLD",
        "passed": overall and all(controls.values()),
        "selected_representation": selected,
        "representation_validated": representation_validated,
        "decision_fidelity_validated": fidelity_validated,
        "calibration_fidelity_passed": calibration_result.get("fidelity_passed") is True,
        "controls": controls,
        "controls_passed": sum(controls.values()),
        "control_count": len(controls),
        "analysis": analysis,
        "calibration_result_sha256": sha256_path(ROOT / "results" / "dev020-calibration-result.json"),
        "selection_freeze_sha256": sha256_path(selection_path),
        "validation_prediction_freeze_sha256": sha256_path(freeze_path),
        "training_steps": 0,
        "heldout_validation_accessed": True,
        "transfer_authorized": False,
        "binding_authority": False,
        "claim_boundary": (
            "One frozen-model synthetic interface-calibration signal only. A pass validates representation stability "
            "and authenticated certificate copying, not learned temporal execution, transfer, production authority, or IGI."
        ),
        "next_gate": "freeze the validated interface for native Program-001 training" if overall else "repair the interface instrument before training",
    }
    write_json(ROOT / "results" / "dev020-interface-result.json", result)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if all(controls.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
