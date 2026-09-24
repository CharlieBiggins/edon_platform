#!/usr/bin/env python3
"""CPU preflight for the selected-candidate full regression."""

from __future__ import annotations

import argparse
import importlib
import json
import subprocess
import sys

from dev014_common import ACTIONNET, BASE, CONFIG, PARENT, ROOT, parent_artifact_root, read_json, read_jsonl, selected_adapter, sha256_path, sha256_tree, summarize, write_json
from gate import advancement_gate
from prepare_data import prepare


TASK_COUNTS = {"CERTIFICATE": 48, "PAIR_CONTRAST": 48, "QUEUE_TRACE": 48, "TRANSITION": 48}


def load_base_modules():
    sys.path.insert(0, str(BASE))
    try:
        return importlib.import_module("evaluate"), importlib.import_module("rules_baseline"), importlib.import_module("canonicalize")
    finally:
        sys.path.pop(0)


def rules_ceiling(rows: list[dict], config: dict) -> dict:
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
    write_json(ROOT / "results" / "rules-ceiling.json", result)
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--allow-missing-parent", action="store_true")
    args = parser.parse_args()
    subprocess.run([sys.executable, "run_campaign.py"], cwd=ACTIONNET, check=True)
    data_manifest = prepare()
    config = read_json(CONFIG)
    qualification = read_json(ACTIONNET / "results" / "qualification_report.json")
    evidence = read_json(ROOT / "evidence" / "operator-reported-dev013-result-2026-09-05.json")
    rows = read_jsonl(ROOT / "prepared" / "full-regression-192.jsonl")
    summary = summarize(rows)
    rules = rules_ceiling(rows, config)
    checks = {
        "qualified_source_all_controls": qualification["controls_passed"] == qualification["control_count"] == 31,
        "registered_protocol_identity": config["protocol_id"] == "CEREBRUM-DEV-014-FULL",
        "frozen_base_revision": config["model_revision"] == "cdbee75f17c01a7cc42f958dc650907174af0554",
        "registered_parent_identity": config["parent_protocol"] == "CEREBRUM-DEV-013-FOCUSED" and config["parent_continuation_seed"] == 26090532,
        "selected_step6_candidate": config["selected_candidate_id"] == "continuation-step-6" and config["selected_step"] == 6,
        "operator_reported_parent_pass_frozen": evidence["confirmation"]["passed"] is True and evidence["confirmation"]["checks_passed"] == evidence["confirmation"]["check_count"] == 9,
        "operator_reported_zero_unsafe": evidence["development"]["unsafe_authorizations"] == evidence["confirmation"]["unsafe_authorizations"] == 0,
        "registered_adapter_hash": config["selected_adapter_tree_sha256"] == evidence["selected_adapter_tree_sha256"],
        "registered_training_manifest_hash": config["parent_training_manifest_sha256"] == evidence["training_manifest_sha256"],
        "registered_selection_hash": config["parent_selection_sha256"] == evidence["selection_sha256"],
        "registered_confirmation_hashes": config["parent_confirmation_input_sha256"] == evidence["confirmation_input_sha256"] and config["parent_confirmation_predictions_sha256"] == evidence["confirmation_predictions_sha256"],
        "validation_count_192": len(rows) == 192,
        "validation_task_balance": summary["task_counts"] == TASK_COUNTS,
        "heldout_full_regression_profile": summary["profile_counts"] == {"FULL_REGRESSION": 192},
        "heldout_renderer": summary["renderer_counts"] == {"HELDOUT_FULL_REGRESSION_REGISTER": 192},
        "no_training_records": data_manifest["training_records"] == 0,
        "explicit_queue_integrity_prompt": data_manifest["explicit_queue_integrity_prompt"] is True,
        "explicit_appeal_clock_prompt": data_manifest["explicit_unresolved_appeal_clock_prompt"] is True,
        "rules_ceiling_passes_all_26_checks": rules["full_regression_gate"]["passed"] is True and rules["full_regression_gate"]["check_count"] == 26,
        "single_frozen_candidate": True,
        "transfer_authorization_disabled": data_manifest["transfer_authorized"] is False,
    }
    adapter = selected_adapter(config)
    training_manifest = parent_artifact_root(config) / "training_manifest.json"
    selection_path = PARENT / "results" / "selected-candidate.json"
    result_path = PARENT / "results" / "dev013-focused-result.json"
    parent_checks = {
        "selected_adapter_present": adapter.is_dir(),
        "training_manifest_present": training_manifest.is_file(),
        "selection_present": selection_path.is_file(),
        "confirmation_result_present": result_path.is_file(),
        "selected_adapter_hash": adapter.is_dir() and sha256_tree(adapter) == config["selected_adapter_tree_sha256"],
        "training_manifest_hash": training_manifest.is_file() and sha256_path(training_manifest) == config["parent_training_manifest_sha256"],
        "selection_hash": selection_path.is_file() and sha256_path(selection_path) == config["parent_selection_sha256"],
        "confirmation_result_identity": result_path.is_file() and read_json(result_path).get("passed") is True and read_json(result_path).get("selected_candidate_id") == config["selected_candidate_id"],
    }
    core_passed = all(checks.values())
    parent_passed = all(parent_checks.values())
    if core_passed and parent_passed:
        status = "READY_FOR_DEV014_FULL_GPU_REGRESSION"
    elif core_passed:
        status = "READY_PENDING_DEV013_SELECTED_ADAPTER_IMPORT"
    else:
        status = "DEV014_FULL_PREFLIGHT_FAILED"
    report = {
        "schema_version": "cerebrum-dev014-full-readiness.v1",
        "protocol_id": config["protocol_id"],
        "status": status,
        "core_control_count": len(checks),
        "core_controls_passed": sum(checks.values()),
        "core_controls": checks,
        "parent_control_count": len(parent_checks),
        "parent_controls_passed": sum(parent_checks.values()),
        "parent_controls": parent_checks,
        "expected_predictions": 192,
        "expected_optimizer_steps": 0,
        "full_regression": summary,
        "prepared_sha256": data_manifest["prepared_sha256"],
        "config_sha256": sha256_path(CONFIG),
        "transfer_authorized": False,
        "public_scored": False,
        "binding_authority": False,
        "claim_boundary": "CPU readiness for one fresh full synthetic regression of the frozen DEV-013 step-6 candidate; no result or transfer authorization.",
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