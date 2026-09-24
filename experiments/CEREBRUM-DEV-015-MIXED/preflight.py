#!/usr/bin/env python3
"""CPU preflight for mixed multi-task retention repair."""

from __future__ import annotations

import argparse
import importlib
import json
import subprocess
import sys

from dev015_common import ACTIONNET, BASE, CONFIG, PARENT, ROOT, parent_adapter, parent_artifact_root, read_json, read_jsonl, sha256_path, sha256_tree, summarize, write_json
from gate import advancement_gate
from prepare_data import prepare


TRAIN_TASKS = {
    "CERTIFICATE": 64,
    "PAIR_CONTRAST": 64,
    "QUEUE_ORDER": 32,
    "QUEUE_PARTITION": 32,
    "QUEUE_TRACE": 96,
    "TRANSITION": 96,
}
DEVELOPMENT_TASKS = {"CERTIFICATE": 16, "PAIR_CONTRAST": 16, "QUEUE_TRACE": 16, "TRANSITION": 16}
CONFIRMATION_TASKS = {"CERTIFICATE": 48, "PAIR_CONTRAST": 48, "QUEUE_TRACE": 48, "TRANSITION": 48}


def load_base_modules():
    sys.path.insert(0, str(BASE))
    try:
        return importlib.import_module("evaluate"), importlib.import_module("rules_baseline"), importlib.import_module("canonicalize")
    finally:
        sys.path.pop(0)


def rules_ceiling(rows: list[dict], config: dict, name: str) -> dict:
    evaluator, rules, canonicalize = load_base_modules()
    predictions = []
    for row in rows:
        parsed = rules.predict_input(row["compiler_input"])
        predictions.append({
            "case_id": row["case_id"],
            "task_type": row["task_type"],
            "parsed": parsed,
            "compiled": canonicalize.compile_prediction(row["task_type"], row["compiler_input"], parsed),
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
    evidence = read_json(ROOT / "evidence" / "operator-reported-dev014-result-2026-09-05.json")
    train = read_jsonl(ROOT / "prepared" / "train.jsonl")
    development = read_jsonl(ROOT / "prepared" / "development-selection-64.jsonl")
    confirmation = read_jsonl(ROOT / "prepared" / "untouched-confirmation-192.jsonl")
    summaries = {
        "train": summarize(train),
        "development_selection": summarize(development),
        "untouched_confirmation": summarize(confirmation),
    }
    development_rules = rules_ceiling(development, config, "development")
    confirmation_rules = rules_ceiling(confirmation, config, "confirmation")
    case_sets = [{row["case_id"] for row in rows} for rows in (train, development, confirmation)]
    pair_sets = [{row["counterfactual_pair_id"] for row in rows} for rows in (train, development, confirmation)]
    checks = {
        "qualified_source_all_controls": qualification["controls_passed"] == qualification["control_count"] == 37,
        "registered_protocol_identity": config["protocol_id"] == "CEREBRUM-DEV-015-MIXED",
        "frozen_base_revision": config["model_revision"] == "cdbee75f17c01a7cc42f958dc650907174af0554",
        "registered_parent_identity": config["parent_protocol"] == "CEREBRUM-DEV-013-FOCUSED" and config["parent_selected_candidate_id"] == "continuation-step-6" and config["parent_selected_step"] == 6,
        "registered_parent_hashes": config["parent_adapter_tree_sha256"] == evidence["adapter_tree_sha256"] and config["dev014_input_sha256"] == evidence["input_sha256"] and config["dev014_predictions_sha256"] == evidence["predictions_sha256"],
        "operator_reported_dev014_hold_frozen": evidence["passed"] is False and evidence["checks_passed"] == 16 and evidence["check_count"] == 26,
        "operator_reported_safety_retained": evidence["zero_unsafe_authorizations"] is True,
        "operator_reported_state_regression_frozen": evidence["transition_exact"] == 0.22916666666666666 and evidence["queue_exact"] == 0.0625,
        "fresh_continuation_seed": config["continuation_seed"] == 26090542,
        "registered_24_optimizer_steps": config["max_steps"] == 24,
        "registered_checkpoints_12_and_24": config["save_steps"] == 12 and [row["step"] for row in config["development_candidates"]] == [12, 24],
        "low_continuation_learning_rate": config["learning_rate"] == 0.000003,
        "effective_batch_16": config["effective_batch_size"] == 16,
        "train_count_384": len(train) == 384,
        "development_count_64": len(development) == 64,
        "confirmation_count_192": len(confirmation) == 192,
        "registered_training_task_mix": summaries["train"]["task_counts"] == TRAIN_TASKS,
        "development_task_balance": summaries["development_selection"]["task_counts"] == DEVELOPMENT_TASKS,
        "confirmation_task_balance": summaries["untouched_confirmation"]["task_counts"] == CONFIRMATION_TASKS,
        "training_source_mix": summaries["train"]["source_counts"] == {"ACTIONNET-DATA-QUAL-010": 352, "ACTIONNET-DATA-QUAL-013": 32},
        "transition_and_queue_emphasized": summaries["train"]["task_counts"]["TRANSITION"] == summaries["train"]["task_counts"]["QUEUE_TRACE"] == 96,
        "splits_case_disjoint": not (case_sets[0] & case_sets[1] or case_sets[0] & case_sets[2] or case_sets[1] & case_sets[2]),
        "splits_pair_disjoint": not (pair_sets[0] & pair_sets[1] or pair_sets[0] & pair_sets[2] or pair_sets[1] & pair_sets[2]),
        "dev014_cases_excluded_from_training": data_manifest["dev014_cases_used_for_training"] is False,
        "two_registered_candidates": len(config["development_candidates"]) == 2,
        "deterministic_selection_ranking": config["selection_ranking"] == ["queue_exact_desc", "transition_exact_desc", "certificate_decision_desc", "unresolved_appeal_desc", "pair_exact_desc", "step_asc"],
        "larger_transition_generation_limit": config["task_token_limits"]["TRANSITION"] == 2048,
        "development_rules_ceiling_passes_26": development_rules["full_regression_gate"]["passed"] is True and development_rules["full_regression_gate"]["check_count"] == 26,
        "confirmation_rules_ceiling_passes_26": confirmation_rules["full_regression_gate"]["passed"] is True and confirmation_rules["full_regression_gate"]["check_count"] == 26,
        "confirmation_single_use": config["confirmation_single_use"] is True and data_manifest["confirmation_single_use"] is True,
        "full_regression_confirmation": data_manifest["full_regression_confirmation"] is True,
        "transfer_authorization_disabled": data_manifest["transfer_authorized"] is False,
    }
    adapter = parent_adapter(config)
    parent_manifest = parent_artifact_root(config) / "training_manifest.json"
    selection_path = PARENT / "results" / "selected-candidate.json"
    result_path = PARENT / "results" / "dev013-focused-result.json"
    parent_checks = {
        "parent_adapter_present": adapter.is_dir(),
        "parent_adapter_hash": adapter.is_dir() and sha256_tree(adapter) == config["parent_adapter_tree_sha256"],
        "parent_training_manifest_present": parent_manifest.is_file(),
        "parent_training_manifest_hash": parent_manifest.is_file() and sha256_path(parent_manifest) == config["parent_training_manifest_sha256"],
        "parent_selection_present": selection_path.is_file(),
        "parent_selection_hash": selection_path.is_file() and sha256_path(selection_path) == config["parent_selection_sha256"],
        "parent_confirmation_result_present": result_path.is_file(),
        "parent_confirmation_result_passed": result_path.is_file() and read_json(result_path).get("passed") is True,
    }
    core_passed = all(checks.values())
    parent_passed = all(parent_checks.values())
    if core_passed and parent_passed:
        status = "READY_FOR_DEV015_MIXED_GPU_EXECUTION"
    elif core_passed:
        status = "READY_PENDING_DEV013_SELECTED_ADAPTER_IMPORT"
    else:
        status = "DEV015_MIXED_PREFLIGHT_FAILED"
    report = {
        "schema_version": "cerebrum-dev015-mixed-readiness.v1",
        "protocol_id": config["protocol_id"],
        "status": status,
        "core_control_count": len(checks),
        "core_controls_passed": sum(checks.values()),
        "core_controls": checks,
        "parent_control_count": len(parent_checks),
        "parent_controls_passed": sum(parent_checks.values()),
        "parent_controls": parent_checks,
        "expected_optimizer_steps": 24,
        "expected_development_predictions": 128,
        "expected_confirmation_predictions_if_selected": 192,
        "splits": summaries,
        "prepared_hashes": data_manifest["prepared_hashes"],
        "config_sha256": sha256_path(CONFIG),
        "full_regression_confirmation": True,
        "transfer_authorized": False,
        "public_scored": False,
        "binding_authority": False,
        "claim_boundary": "Mixed-retention repair readiness only; no learned checkpoint, confirmation, seed-reproducibility, transfer, production, authority, or IGI result.",
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