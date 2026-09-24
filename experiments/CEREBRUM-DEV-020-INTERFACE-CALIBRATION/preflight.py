#!/usr/bin/env python3
"""CPU preflight for representation-equivalence and decision-fidelity calibration."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys

from dev020_common import (
    ACTIONNET,
    CONFIG,
    MODEL_PARENT,
    PREDECESSOR,
    ROOT,
    model_adapter,
    read_json,
    read_jsonl,
    sha256_path,
    sha256_tree,
    write_json,
)
from prepare_data import BASE_SYSTEM_PROMPT, prepare_calibration


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--allow-missing-parent", action="store_true")
    args = parser.parse_args()
    subprocess.run([sys.executable, "run_campaign.py"], cwd=ACTIONNET, check=True)
    subprocess.run([sys.executable, "audit_dev019.py"], cwd=ROOT, check=True)
    data_manifest = prepare_calibration()
    config = read_json(CONFIG)
    qualification = read_json(ACTIONNET / "results" / "qualification_report.json")
    audit = read_json(ROOT / "evidence" / "dev019-implementation-audit.json")
    operator = read_json(ROOT / "evidence" / "operator-reported-dev019-result-2026-09-07.json")
    rows = read_jsonl(ROOT / "prepared" / "format-calibration-384.jsonl")
    representation_rows = [row for row in rows if row["calibration_arm"] == "REPRESENTATION"]
    fidelity_rows = [row for row in rows if row["calibration_arm"] == "DECISION_FIDELITY"]
    scenarios = {row["calibration_scenario_id"] for row in rows}
    checks = {
        "qualified_source_all_controls": qualification["controls_passed"] == qualification["control_count"],
        "registered_protocol_identity": config["protocol_id"] == "CEREBRUM-DEV-020-INTERFACE-CALIBRATION",
        "zero_training_steps": config["training_steps"] == data_manifest["training_records"] == 0,
        "training_not_authorized": config["training_authorized"] is False and data_manifest["training_authorized"] is False,
        "registered_calibration_count_384": len(rows) == config["registered_calibration_predictions"] == 384,
        "registered_calibration_scenarios_64": len(scenarios) == config["registered_calibration_scenarios"] == 64,
        "six_conditions_per_scenario": all(
            len([row for row in rows if row["calibration_scenario_id"] == scenario]) == 6
            for scenario in scenarios
        ),
        "representation_count_320": len(representation_rows) == 320,
        "fidelity_count_64": len(fidelity_rows) == 64,
        "representation_system_matches_parent": all(
            row["prompt"].startswith(f"SYSTEM\n{BASE_SYSTEM_PROMPT}") for row in representation_rows
        ),
        "representation_task_identical": len({row["compiler_input"]["query"] for row in representation_rows}) == 1,
        "direct_observation_not_nested_packet": all(
            "raw_observation" not in row["compiler_input"]["observation"]["content"]
            and "predecision_state" not in row["compiler_input"]["observation"]["content"]
            for row in representation_rows
        ),
        "neutral_representation_labels": all("GOLD" not in row["prompt"].upper() for row in rows),
        "fidelity_instruction_immutable": all(
            "fields are immutable" in row["prompt"] and "without recomputing" in row["prompt"]
            for row in fidelity_rows
        ),
        "fidelity_source_authenticated": all(
            "AUTHENTICATED_DETERMINISTIC_EXECUTOR" in row["prompt"] for row in fidelity_rows
        ),
        "dev019_audit_complete": audit["findings_supported"] == audit["finding_count"] == 17,
        "dev019_audit_identifies_manipulation_failure": audit["findings"]["same_key_set_but_not_same_value_distribution"] is True,
        "operator_result_records_nonmonotonicity": (
            operator["typed_to_ordered_decision_degradations"] == 11
            and operator["typed_to_ordered_exact_degradations"] == 15
        ),
        "frozen_base_revision": config["model_revision"] == "cdbee75f17c01a7cc42f958dc650907174af0554",
        "heldout_selection_registered": config["registered_heldout_predictions_after_selection"] == 192,
        "transfer_authorization_disabled": config["transfer_authorized"] is False,
    }
    adapter = model_adapter(config)
    predecessor_result = PREDECESSOR / "results" / "dev019-diagnostic-result.json"
    predecessor_freeze = PREDECESSOR / "results" / "diagnostic-prediction-freeze.json"
    predecessor_predictions = PREDECESSOR / "results" / "diagnostic-predictions.jsonl"
    result_value = read_json(predecessor_result) if predecessor_result.is_file() else {}
    freeze_value = read_json(predecessor_freeze) if predecessor_freeze.is_file() else {}
    parent_checks = {
        "operator_predecessor_status": operator["status"] == config["scientific_predecessor_status"],
        "operator_prediction_freeze_hash": operator["prediction_freeze_sha256"] == config["scientific_predecessor_prediction_freeze_sha256"],
        "operator_predictions_hash": operator["predictions_sha256"] == config["scientific_predecessor_predictions_sha256"],
        "predecessor_result_present": predecessor_result.is_file(),
        "predecessor_result_complete": (
            result_value.get("status") == config["scientific_predecessor_status"]
            and result_value.get("passed") is True
            and result_value.get("training_steps") == 0
        ),
        "predecessor_result_binds_freeze": (
            result_value.get("prediction_freeze_sha256") == config["scientific_predecessor_prediction_freeze_sha256"]
        ),
        "predecessor_freeze_present": predecessor_freeze.is_file(),
        "predecessor_freeze_hash": (
            predecessor_freeze.is_file()
            and sha256_path(predecessor_freeze) == config["scientific_predecessor_prediction_freeze_sha256"]
        ),
        "predecessor_predictions_present": predecessor_predictions.is_file(),
        "predecessor_predictions_hash": (
            predecessor_predictions.is_file()
            and sha256_path(predecessor_predictions) == config["scientific_predecessor_predictions_sha256"]
        ),
        "predecessor_predictions_bound": (
            freeze_value.get("predictions_sha256") == config["scientific_predecessor_predictions_sha256"]
        ),
        "frozen_model_adapter_present": adapter.is_dir(),
        "frozen_model_adapter_hash": adapter.is_dir() and sha256_tree(adapter) == config["model_parent_adapter_tree_sha256"],
    }
    core_passed = all(checks.values())
    parent_passed = all(parent_checks.values())
    if core_passed and parent_passed:
        status = "READY_FOR_DEV020_INTERFACE_CALIBRATION_GPU_EXECUTION"
    elif core_passed:
        status = "READY_PENDING_DEV019_RESULT_AND_DEV017_ADAPTER_IMPORT"
    else:
        status = "DEV020_INTERFACE_PREFLIGHT_FAILED"
    report = {
        "schema_version": "cerebrum-dev020-interface-readiness.v1",
        "protocol_id": config["protocol_id"],
        "status": status,
        "core_control_count": len(checks),
        "core_controls_passed": sum(checks.values()),
        "core_controls": checks,
        "parent_control_count": len(parent_checks),
        "parent_controls_passed": sum(parent_checks.values()),
        "parent_controls": parent_checks,
        "expected_training_steps": 0,
        "expected_calibration_scenarios": 64,
        "expected_calibration_predictions": 384,
        "expected_heldout_predictions_if_selected": 192,
        "candidate_representations": config["candidate_representations"],
        "baseline_representation": config["baseline_representation"],
        "fidelity_condition": config["fidelity_condition"],
        "prepared_sha256": data_manifest["prepared_sha256"],
        "audit_sha256": sha256_path(ROOT / "evidence" / "dev019-implementation-audit.json"),
        "config_sha256": sha256_path(CONFIG),
        "training_steps": 0,
        "transfer_authorized": False,
        "binding_authority": False,
        "claim_boundary": (
            "Interface-calibration readiness only; no learned repair, transfer, production authority, or IGI result."
        ),
    }
    write_json(ROOT / "results" / "readiness-report.json", report)
    print(json.dumps(report, indent=2, sort_keys=True))
    if not core_passed:
        return 1
    if not parent_passed and not args.allow_missing_parent:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
