#!/usr/bin/env python3
"""CPU preflight for the frozen-model gold-intervention diagnostic."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys

from dev019_common import (
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
from prepare_data import prepare


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--allow-missing-parent", action="store_true")
    args = parser.parse_args()
    subprocess.run([sys.executable, "run_campaign.py"], cwd=ACTIONNET, check=True)
    data_manifest = prepare()
    config = read_json(CONFIG)
    qualification = read_json(ACTIONNET / "results" / "qualification_report.json")
    evidence = read_json(ROOT / "evidence" / "operator-reported-dev018-result-2026-09-06.json")
    rows = read_jsonl(ROOT / "prepared" / "diagnostic-matrix-160.jsonl")
    scenarios = {row["diagnostic_scenario_id"] for row in rows}
    checks = {
        "qualified_source_all_controls": qualification["controls_passed"] == qualification["control_count"],
        "registered_protocol_identity": config["protocol_id"] == "CEREBRUM-DEV-019-DIAGNOSTIC",
        "zero_training_steps": config["training_steps"] == data_manifest["training_records"] == 0,
        "training_not_authorized": config["training_authorized"] is False and data_manifest["training_authorized"] is False,
        "registered_record_count_160": len(rows) == config["registered_predictions"] == 160,
        "registered_scenario_count_32": len(scenarios) == config["registered_scenarios"] == 32,
        "five_conditions_per_scenario": all(
            len([row for row in rows if row["diagnostic_scenario_id"] == scenario]) == 5
            for scenario in scenarios
        ),
        "condition_counts_32_each": all(
            sum(row["diagnostic_condition"] == condition for row in rows) == 32
            for condition in config["diagnostic_conditions"]
        ),
        "targets_identical_within_scenario": data_manifest["targets_identical_within_scenario"] is True,
        "frozen_base_revision": config["model_revision"] == "cdbee75f17c01a7cc42f958dc650907174af0554",
        "repeated_measures_registered": data_manifest["repeated_measures"] is True,
        "dev018_confirmation_not_reused": data_manifest["dev018_confirmation_reused"] is False,
        "causal_claim_boundary_registered": config["causal_claim_boundary"].startswith("earliest demonstrated failure"),
        "transfer_authorization_disabled": config["transfer_authorized"] is False,
    }
    adapter = model_adapter(config)
    predecessor_result = PREDECESSOR / "results" / "dev018-verified-result.json"
    predecessor_model_predictions = PREDECESSOR / "results" / "confirmation-model-predictions.jsonl"
    predecessor_verification_audit = PREDECESSOR / "results" / "confirmation-verification-audit.jsonl"
    predecessor_full_audit = PREDECESSOR / "results" / "dev018-full-error-audit.json"
    result_value = read_json(predecessor_result) if predecessor_result.is_file() else {}
    full_audit_value = read_json(predecessor_full_audit) if predecessor_full_audit.is_file() else {}
    parent_checks = {
        "dev018_operator_status_frozen": evidence["status"] == config["scientific_predecessor_status"],
        "dev018_operator_result_hash_frozen": evidence["final_result_sha256"] == config["scientific_predecessor_result_sha256"],
        "dev018_result_present": predecessor_result.is_file(),
        "dev018_result_hash": predecessor_result.is_file() and sha256_path(predecessor_result) == config["scientific_predecessor_result_sha256"],
        "dev018_result_passed_hybrid_only": (
            result_value.get("status") == config["scientific_predecessor_status"]
            and result_value.get("passed") is True
            and result_value.get("model_only_metrics", {}).get("full_regression_gate", {}).get("passed") is False
            and result_value.get("verified_hybrid_metrics", {}).get("full_regression_gate", {}).get("passed") is True
        ),
        "dev018_confirmation_model_predictions_present": predecessor_model_predictions.is_file(),
        "dev018_confirmation_model_predictions_hash": (
            predecessor_model_predictions.is_file()
            and sha256_path(predecessor_model_predictions) == config["scientific_predecessor_confirmation_model_predictions_sha256"]
        ),
        "dev018_confirmation_verification_audit_present": predecessor_verification_audit.is_file(),
        "dev018_confirmation_verification_audit_hash": (
            predecessor_verification_audit.is_file()
            and sha256_path(predecessor_verification_audit) == config["scientific_predecessor_confirmation_verification_audit_sha256"]
        ),
        "dev018_full_error_audit_present": predecessor_full_audit.is_file(),
        "dev018_full_error_audit_signature": (
            full_audit_value.get("status") == evidence["full_error_audit_status"]
            and full_audit_value.get("combined", {}).get("cases") == evidence["combined_cases"]
            and full_audit_value.get("combined", {}).get("accepted") == evidence["combined_accepted_model_outputs"]
            and full_audit_value.get("combined", {}).get("overridden") == evidence["combined_overridden_model_outputs"]
            and full_audit_value.get("combined", {}).get("safety_overrides") == evidence["combined_safety_overrides"]
        ),
        "frozen_model_adapter_present": adapter.is_dir(),
        "frozen_model_adapter_hash": adapter.is_dir() and sha256_tree(adapter) == config["model_parent_adapter_tree_sha256"],
    }
    core_passed = all(checks.values())
    parent_passed = all(parent_checks.values())
    if core_passed and parent_passed:
        status = "READY_FOR_DEV019_DIAGNOSTIC_GPU_EXECUTION"
    elif core_passed:
        status = "READY_PENDING_DEV018_RESULT_AND_DEV017_ADAPTER_IMPORT"
    else:
        status = "DEV019_DIAGNOSTIC_PREFLIGHT_FAILED"
    report = {
        "schema_version": "cerebrum-dev019-diagnostic-readiness.v1",
        "protocol_id": config["protocol_id"],
        "status": status,
        "core_control_count": len(checks),
        "core_controls_passed": sum(checks.values()),
        "core_controls": checks,
        "parent_control_count": len(parent_checks),
        "parent_controls_passed": sum(parent_checks.values()),
        "parent_controls": parent_checks,
        "expected_training_steps": 0,
        "expected_scenarios": 32,
        "expected_predictions": 160,
        "conditions": config["diagnostic_conditions"],
        "prepared_sha256": data_manifest["prepared_sha256"],
        "config_sha256": sha256_path(CONFIG),
        "confirmation": False,
        "transfer_authorized": False,
        "binding_authority": False,
        "claim_boundary": "Gold-intervention diagnostic readiness only; no learned repair, confirmation, transfer, production authority, or IGI result.",
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