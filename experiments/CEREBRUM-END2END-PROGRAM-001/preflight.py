#!/usr/bin/env python3
"""CPU preflight for native temporal-program training."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys

from prepare_data import prepare
from program_common import ACTIONNET, CONFIG, DEV020, IR, ROOT, read_json, read_jsonl, sha256_path, write_json


def interface_controls(config: dict, allow_operator_evidence: bool) -> tuple[dict[str, bool], str]:
    freeze_path = DEV020 / "results" / "dev020-result-freeze.json"
    audit_path = DEV020 / "results" / "dev020-final-error-audit.json"
    result_path = DEV020 / "results" / "dev020-interface-result.json"
    if freeze_path.is_file() and audit_path.is_file() and result_path.is_file():
        freeze = read_json(freeze_path)
        audit = read_json(audit_path)
        result = read_json(result_path)
        hashes = freeze.get("source_hashes", {})
        return ({
            "dev020_final_result_passed": result.get("status") == config["interface_predecessor_status"] and result.get("passed") is True,
            "dev020_result_freeze_ready": freeze.get("status") == "DEV020_INTERFACE_FROZEN_FOR_PROGRAM001",
            "dev020_selected_interface_exact": freeze.get("selected_representation") == config["validated_interface"],
            "dev020_selection_hash_bound": hashes.get("selection_freeze") == config["interface_selection_sha256"],
            "dev020_calibration_result_hash_bound": hashes.get("calibration_result") == config["interface_calibration_result_sha256"],
            "dev020_validation_input_hash_bound": hashes.get("validation_input") == config["interface_validation_input_sha256"],
            "dev020_validation_predictions_hash_bound": hashes.get("validation_predictions") == config["interface_validation_predictions_sha256"],
            "dev020_error_audit_bound": freeze.get("error_audit_sha256") == sha256_path(audit_path),
            "dev020_unsafe_repair_required": audit.get("interpretation", {}).get("unsafe_failure_repair_still_required") is True,
        }, "ACTUAL_MODAL_FREEZE")
    evidence_path = DEV020 / "evidence" / "operator-reported-dev020-result-2026-09-07.json"
    if not allow_operator_evidence or not evidence_path.is_file():
        return ({"actual_dev020_result_freeze_present": False}, "MISSING_ACTUAL_MODAL_FREEZE")
    evidence = read_json(evidence_path)
    return ({
        "operator_reported_dev020_passed": evidence.get("status") == config["interface_predecessor_status"] and evidence.get("passed") is True,
        "operator_reported_selected_interface": evidence.get("selected_representation") == config["validated_interface"],
        "operator_reported_selection_hash": evidence.get("selection_freeze_sha256") == config["interface_selection_sha256"],
        "operator_reported_calibration_result_hash": evidence.get("calibration_result_sha256") == config["interface_calibration_result_sha256"],
        "operator_reported_validation_input_hash": evidence.get("heldout", {}).get("input_sha256") == config["interface_validation_input_sha256"],
        "operator_reported_validation_predictions_hash": evidence.get("heldout", {}).get("predictions_sha256") == config["interface_validation_predictions_sha256"],
        "actual_dev020_result_freeze_present": False,
    }, "OPERATOR_EVIDENCE_ONLY")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--allow-operator-evidence", action="store_true")
    args = parser.parse_args()
    subprocess.run([sys.executable, "run_campaign.py"], cwd=ACTIONNET, check=True)
    manifest = prepare()
    config = read_json(CONFIG)
    qualification = read_json(ACTIONNET / "results" / "qualification_report.json")
    interface_spec = read_json(ROOT / "evidence" / "validated-interface-spec.json")
    train = read_jsonl(ROOT / "prepared" / "train-1024.jsonl")
    development = read_jsonl(ROOT / "prepared" / "development-selection-128.jsonl")
    confirmation = read_jsonl(ROOT / "prepared" / "untouched-confirmation-256.jsonl")
    interface, interface_mode = interface_controls(config, args.allow_operator_evidence)
    case_sets = [{row["case_id"] for row in rows} for rows in (train, development, confirmation)]
    pair_sets = [{row["counterfactual_pair_id"] for row in rows} for rows in (train, development, confirmation)]
    oracle_checks = []
    for row in development:
        source = row["compiler_input"]
        oracle_checks.append(IR.verify_program(
            row["completion"],
            source["program_source"]["initial_state"],
            source["program_source"]["submitted_events"],
            source["oracle_state"],
            source["oracle_certificate"],
        ))
    exposures = config["effective_batch_size"] * config["max_steps"]
    checks = {
        "qualified_source_all_controls": qualification["controls_passed"] == qualification["control_count"],
        "registered_protocol_identity": config["protocol_id"] == "CEREBRUM-END2END-PROGRAM-001",
        "frozen_base_revision": config["model_revision"] == "cdbee75f17c01a7cc42f958dc650907174af0554",
        "fresh_adapter_from_base": config["fresh_adapter_from_base"] is True,
        "no_parent_adapter": config["base_control"]["adapter"] is None,
        "untrained_step_zero_base_control_registered": (
            config["base_control"]["candidate_id"] == "untrained-base-step-0"
            and config["base_control"]["step"] == 0
            and config["registered_development_predictions"] == 3 * len(development) == 384
            and config["registered_confirmation_predictions_after_selection"] == 2 * len(confirmation) == 512
        ),
        "base_development_prediction_precedes_training": (
            config["base_control"]["development_prediction_before_training"] is True
        ),
        "paired_base_confirmation_registered": (
            config["base_control"]["paired_confirmation_if_selected"] is True
        ),
        "validated_interface_registered": config["validated_interface"] == "FAMILIAR_AUGMENTED",
        "validated_interface_spec_frozen": (
            interface_spec["interface_id"] == "FAMILIAR_AUGMENTED-v1"
            and interface_spec["selection_freeze_sha256"] == config["interface_selection_sha256"]
            and interface_spec["single_source"] is True
            and interface_spec["heldout_evidence"]["decision_agreement"] == 64
            and interface_spec["heldout_evidence"]["interface_unsafe_authorizations"] == 9
        ),
        "native_program_schema_registered": config["program_schema"] == "ACTIONNET_TEMPORAL_PROGRAM_V1",
        "train_count_1024": len(train) == config["training_records"] == 1024,
        "development_count_128": len(development) == config["development_records"] == 128,
        "confirmation_count_256": len(confirmation) == config["confirmation_records"] == 256,
        "two_complete_training_passes": exposures == config["registered_effective_sample_exposures"] == 2048 and exposures / len(train) == 2,
        "registered_checkpoints_64_and_128": [row["step"] for row in config["development_candidates"]] == [64, 128],
        "development_improvement_gate_registered": set(config["development_improvement_gate"]) == {
            "program_exact_delta_floor",
            "executed_state_delta_floor",
            "decision_delta_floor",
            "verifier_acceptance_delta_floor",
            "program_exact_mcnemar_p_ceiling",
            "unsafe_authorization_delta_ceiling",
        },
        "confirmation_improvement_gate_registered": set(config["confirmation_improvement_gate"]) == {
            "program_exact_delta_floor",
            "executed_state_delta_floor",
            "decision_delta_floor",
            "verifier_acceptance_delta_floor",
            "program_exact_mcnemar_p_ceiling",
            "unsafe_authorization_delta_ceiling",
        },
        "paired_significance_registered": (
            config["development_improvement_gate"]["program_exact_mcnemar_p_ceiling"] <= 0.05
            and config["confirmation_improvement_gate"]["program_exact_mcnemar_p_ceiling"] <= 0.05
        ),
        "selection_ranking_includes_training_effect": (
            config["selection_ranking"][:3]
            == ["absolute_and_improvement_gate_desc", "unsafe_authorizations_asc", "program_exact_delta_desc"]
        ),
        "all_prompts_validated_interface": all(row["selected_renderer"] == "FAMILIAR_AUGMENTED" for row in train + development + confirmation),
        "all_records_fresh": all(row["replay_source_protocol"] == "FRESH" for row in train + development + confirmation),
        "case_splits_disjoint": not (case_sets[0] & case_sets[1] or case_sets[0] & case_sets[2] or case_sets[1] & case_sets[2]),
        "pair_splits_disjoint": not (pair_sets[0] & pair_sets[1] or pair_sets[0] & pair_sets[2] or pair_sets[1] & pair_sets[2]),
        "oracle_programs_parse_and_execute": all(row["accepted_by_verifier"] and row["program_exact"] for row in oracle_checks),
        "independent_interpreter_scoring": manifest["independent_interpreter_scoring"] is True,
        "confirmation_single_use": config["confirmation_single_use"] is True,
        "transfer_authorization_disabled": config["transfer_authorized"] is False,
        "binding_authority_false": config["binding_authority"] is False,
        **interface,
    }
    actual_freeze_ready = interface_mode == "ACTUAL_MODAL_FREEZE" and all(interface.values())
    status = (
        "READY_FOR_PROGRAM001_GPU_EXECUTION"
        if all(checks.values()) and actual_freeze_ready
        else "READY_PENDING_ACTUAL_DEV020_MODAL_FREEZE"
        if interface_mode == "OPERATOR_EVIDENCE_ONLY" and all(value for name, value in checks.items() if name != "actual_dev020_result_freeze_present")
        else "HOLD"
    )
    report = {
        "schema_version": "cerebrum-program-001-readiness.v1",
        "protocol_id": config["protocol_id"],
        "status": status,
        "interface_evidence_mode": interface_mode,
        "checks": checks,
        "checks_passed": sum(checks.values()),
        "check_count": len(checks),
        "source_qualification_sha256": sha256_path(ACTIONNET / "results" / "qualification_report.json"),
        "prepared_manifest_sha256": sha256_path(ROOT / "prepared" / "data-manifest.json"),
        "training_steps": config["max_steps"],
        "transfer_authorized": False,
        "binding_authority": False,
    }
    write_json(ROOT / "results" / "readiness-report.json", report)
    print(json.dumps(report, indent=2, sort_keys=True))
    if status == "READY_FOR_PROGRAM001_GPU_EXECUTION":
        print("READY_FOR_PROGRAM001_GPU_EXECUTION")
        return 0
    if status == "READY_PENDING_ACTUAL_DEV020_MODAL_FREEZE" and args.allow_operator_evidence:
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())