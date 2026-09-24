#!/usr/bin/env python3
"""CPU preflight for the zero-training verified-hybrid experiment."""

from __future__ import annotations

import argparse
import importlib
import json
import subprocess
import sys

from dev018_common import (
    ACTIONNET,
    BASE,
    CONFIG,
    MODEL_PARENT,
    ROOT,
    model_adapter,
    read_json,
    read_jsonl,
    sha256_path,
    sha256_tree,
    summarize,
    write_json,
)
from gate import advancement_gate
from prepare_data import prepare


TASKS_64 = {"CERTIFICATE": 16, "PAIR_CONTRAST": 16, "QUEUE_TRACE": 16, "TRANSITION": 16}
TASKS_192 = {"CERTIFICATE": 48, "PAIR_CONTRAST": 48, "QUEUE_TRACE": 48, "TRANSITION": 48}


def load_base_modules():
    sys.path.insert(0, str(BASE))
    try:
        return (
            importlib.import_module("evaluate"),
            importlib.import_module("rules_baseline"),
            importlib.import_module("canonicalize"),
        )
    finally:
        sys.path.pop(0)


def rules_ceiling(rows: list[dict], config: dict, name: str) -> dict:
    evaluator, rules, compiler = load_base_modules()
    predictions = []
    for row in rows:
        parsed = rules.predict_input(row["compiler_input"])
        predictions.append({
            "case_id": row["case_id"],
            "task_type": row["task_type"],
            "parsed": parsed,
            "compiled": compiler.compile_prediction(row["task_type"], row["compiler_input"], parsed),
            "raw_output": json.dumps(parsed, sort_keys=True),
            "confidence": 1.0,
            "ended_with_eos": True,
            "hit_generation_limit": False,
        })
    result = evaluator.score(predictions, rows, "transparent_rules", None)
    result["full_regression_gate"] = advancement_gate(result, config["gate"])
    write_json(ROOT / "results" / f"rules-{name}-ceiling.json", result)
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--allow-missing-parent", action="store_true")
    args = parser.parse_args()
    subprocess.run([sys.executable, "run_campaign.py"], cwd=ACTIONNET, check=True)
    data_manifest = prepare()
    config = read_json(CONFIG)
    qualification = read_json(ACTIONNET / "results" / "qualification_report.json")
    evidence = read_json(ROOT / "evidence" / "operator-reported-dev017-result-2026-09-06.json")
    development = read_jsonl(ROOT / "prepared" / "development-selection-64.jsonl")
    confirmation = read_jsonl(ROOT / "prepared" / "untouched-confirmation-192.jsonl")
    dev_verifier = read_jsonl(ROOT / "prepared" / "development-verifier-inputs-64.jsonl")
    conf_verifier = read_jsonl(ROOT / "prepared" / "confirmation-verifier-inputs-192.jsonl")
    dev_rules = rules_ceiling(development, config, "development")
    conf_rules = rules_ceiling(confirmation, config, "confirmation")
    case_sets = [{row["case_id"] for row in rows} for rows in (development, confirmation)]
    pair_sets = [{row["counterfactual_pair_id"] for row in rows} for rows in (development, confirmation)]
    checks = {
        "qualified_source_all_controls": qualification["controls_passed"] == qualification["control_count"],
        "registered_protocol_identity": config["protocol_id"] == "CEREBRUM-DEV-018-VERIFIED",
        "zero_training_steps": config["training_steps"] == 0 and data_manifest["training_records"] == 0,
        "training_not_authorized": config["training_authorized"] is False and data_manifest["training_authorized"] is False,
        "frozen_base_revision": config["model_revision"] == "cdbee75f17c01a7cc42f958dc650907174af0554",
        "development_count_64": len(development) == 64,
        "confirmation_count_192": len(confirmation) == 192,
        "development_task_balance": summarize(development)["task_counts"] == TASKS_64,
        "confirmation_task_balance": summarize(confirmation)["task_counts"] == TASKS_192,
        "splits_case_disjoint": not case_sets[0] & case_sets[1],
        "splits_pair_disjoint": not pair_sets[0] & pair_sets[1],
        "development_verifier_inputs_complete": len(dev_verifier) == 64,
        "confirmation_verifier_inputs_complete": len(conf_verifier) == 192,
        "verifier_inputs_exact_fields": all(
            set(row) == {"case_id", "task_type", "compiler_input"}
            for row in dev_verifier + conf_verifier
        ),
        "verifier_inputs_have_no_answer_keys": data_manifest["answer_keys_present_in_verifier_inputs"] is False,
        "acceptance_requires_exact_executor_match": config["verification_policy"]["accept_model_only_if_compiled_output_equals_executor"] is True,
        "all_mismatches_fail_closed": config["verification_policy"]["override_with_executor_on_any_mismatch"] is True,
        "all_overrides_recorded": config["verification_policy"]["record_all_overrides"] is True,
        "answer_key_access_prohibited": config["verification_policy"]["answer_key_access_prohibited"] is True,
        "development_rules_ceiling_passes_26": dev_rules["full_regression_gate"]["passed"] is True,
        "confirmation_rules_ceiling_passes_26": conf_rules["full_regression_gate"]["passed"] is True,
        "model_and_hybrid_scored_separately": data_manifest["model_and_hybrid_scored_separately"] is True,
        "confirmation_single_use": config["confirmation_single_use"] is True,
        "transfer_authorization_disabled": data_manifest["transfer_authorized"] is False,
    }
    candidate = next(
        row for row in evidence["candidates"]
        if row["candidate_id"] == config["model_parent_candidate_id"]
    )
    adapter = model_adapter(config)
    parent_config = MODEL_PARENT / "configs" / "dev017-causal.json"
    parent_predictions = MODEL_PARENT / "results" / "development-continuation-step-24-predictions.jsonl"
    parent_freeze = MODEL_PARENT / "results" / "development-prediction-freeze.json"
    parent_selection = MODEL_PARENT / "results" / "selected-candidate.json"
    parent_result = MODEL_PARENT / "results" / "dev017-causal-result.json"
    parent_audit = MODEL_PARENT / "results" / "dev017-development-error-audit.json"
    freeze_value = read_json(parent_freeze) if parent_freeze.is_file() else {}
    selection_value = read_json(parent_selection) if parent_selection.is_file() else {}
    result_value = read_json(parent_result) if parent_result.is_file() else {}
    audit_value = read_json(parent_audit) if parent_audit.is_file() else {}
    parent_checks = {
        "operator_result_is_negative": evidence["status"] == config["model_parent_status"],
        "operator_confirmation_sealed": evidence["confirmation_scored"] is False and evidence["confirmation_remained_sealed"] is True,
        "engineering_choice_not_scientific_promotion": evidence["engineering_parent_selection_basis"].endswith("not scientific promotion"),
        "registered_parent_hashes": (
            candidate["adapter_tree_sha256"] == config["model_parent_adapter_tree_sha256"]
            and candidate["predictions_sha256"] == config["model_parent_predictions_sha256"]
            and evidence["config_sha256"] == config["model_parent_config_sha256"]
        ),
        "parent_adapter_present": adapter.is_dir(),
        "parent_adapter_hash": adapter.is_dir() and sha256_tree(adapter) == config["model_parent_adapter_tree_sha256"],
        "parent_config_present": parent_config.is_file(),
        "parent_config_hash": parent_config.is_file() and sha256_path(parent_config) == config["model_parent_config_sha256"],
        "parent_predictions_present": parent_predictions.is_file(),
        "parent_predictions_hash": parent_predictions.is_file() and sha256_path(parent_predictions) == config["model_parent_predictions_sha256"],
        "parent_freeze_present": parent_freeze.is_file(),
        "parent_freeze_hash": parent_freeze.is_file() and sha256_path(parent_freeze) == evidence["development_prediction_freeze_sha256"],
        "parent_selection_failed_closed": selection_value.get("status") == config["model_parent_status"] and selection_value.get("selected_candidate_id") is None,
        "parent_result_confirmation_sealed": result_value.get("status") == config["model_parent_status"] and result_value.get("confirmation_scored") is False,
        "parent_error_audit_present": parent_audit.is_file(),
        "parent_error_audit_signature": (
            audit_value.get("shared_failure_count") == evidence["shared_failure_count"]
            and audit_value.get("confirmation_accessed") is False
        ),
    }
    core_passed = all(checks.values())
    parent_passed = all(parent_checks.values())
    if core_passed and parent_passed:
        status = "READY_FOR_DEV018_VERIFIED_GPU_EXECUTION"
    elif core_passed:
        status = "READY_PENDING_DEV017_CHECKPOINT24_IMPORT"
    else:
        status = "DEV018_VERIFIED_PREFLIGHT_FAILED"
    report = {
        "schema_version": "cerebrum-dev018-verified-readiness.v1",
        "protocol_id": config["protocol_id"],
        "status": status,
        "core_control_count": len(checks),
        "core_controls_passed": sum(checks.values()),
        "core_controls": checks,
        "parent_control_count": len(parent_checks),
        "parent_controls_passed": sum(parent_checks.values()),
        "parent_controls": parent_checks,
        "expected_training_steps": 0,
        "expected_development_model_predictions": 64,
        "expected_confirmation_model_predictions_if_development_passes": 192,
        "prepared_hashes": data_manifest["prepared_hashes"],
        "verifier_input_hashes": data_manifest["verifier_input_hashes"],
        "config_sha256": sha256_path(CONFIG),
        "confirmation_single_use": True,
        "binding_authority": False,
        "transfer_authorized": False,
        "claim_boundary": "Verified-hybrid readiness only. The deterministic executor is an explicit system component; no learned-capability, transfer, production, authority, or IGI result.",
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