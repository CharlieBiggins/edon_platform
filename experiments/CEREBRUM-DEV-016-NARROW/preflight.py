#!/usr/bin/env python3
"""CPU preflight for delayed-evidence and exact-state narrow repair."""

from __future__ import annotations

import argparse
import importlib
import json
import subprocess
import sys

from dev016_common import (
    ACTIONNET,
    BASE,
    CONFIG,
    PARENT,
    ROOT,
    parent_adapter,
    parent_artifact_root,
    read_json,
    read_jsonl,
    sha256_path,
    sha256_tree,
    summarize,
    write_json,
)
from gate import advancement_gate
from prepare_data import prepare


TRAIN_TASKS = {
    "CERTIFICATE": 64,
    "PAIR_CONTRAST": 48,
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
        return (
            importlib.import_module("evaluate"),
            importlib.import_module("rules_baseline"),
            importlib.import_module("canonicalize"),
        )
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
    evidence = read_json(ROOT / "evidence" / "operator-reported-dev015-result-2026-09-06.json")
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
    delayed_certificates = [
        row for row in train
        if row["task_type"] == "CERTIFICATE" and row.get("pair_mechanism") == "DELAYED_EVIDENCE"
    ]
    evidence_candidates = {row["candidate_id"]: row for row in evidence["candidates"]}
    checks = {
        "qualified_source_all_controls": qualification["controls_passed"] == qualification["control_count"] == 33,
        "registered_protocol_identity": config["protocol_id"] == "CEREBRUM-DEV-016-NARROW",
        "frozen_base_revision": config["model_revision"] == "cdbee75f17c01a7cc42f958dc650907174af0554",
        "registered_parent_identity": config["parent_protocol"] == "CEREBRUM-DEV-015-MIXED" and config["parent_candidate_id"] == "continuation-step-12" and config["parent_checkpoint_step"] == 12,
        "registered_parent_hashes": config["parent_adapter_tree_sha256"] == evidence_candidates["continuation-step-12"]["adapter_tree_sha256"] and config["parent_development_predictions_sha256"] == evidence_candidates["continuation-step-12"]["predictions_sha256"] and config["parent_config_sha256"] == evidence["config_sha256"],
        "operator_reported_dev015_hold_frozen": evidence["status"] == "NO_DEVELOPMENT_CANDIDATE_PASSES_FULL_GATE" and all(row["checks_passed"] == 23 and row["check_count"] == 26 for row in evidence["candidates"]),
        "operator_reported_confirmation_sealed": evidence["confirmation_scored"] is False and evidence["confirmation_remained_sealed"] is True,
        "operator_reported_failures_frozen": set(evidence["failed_checks"]) == {"certificate_pivotal_floor", "transition_post_state_floor", "zero_unsafe_authorizations"},
        "earlier_equal_metric_parent_choice": evidence["registered_parent_choice"]["candidate_id"] == "continuation-step-12",
        "fresh_continuation_seed": config["continuation_seed"] == 26090612,
        "registered_12_optimizer_steps": config["max_steps"] == 12,
        "registered_checkpoints_6_and_12": config["save_steps"] == 6 and [row["step"] for row in config["development_candidates"]] == [6, 12],
        "low_continuation_learning_rate": config["learning_rate"] == 0.000001,
        "effective_batch_16": config["effective_batch_size"] == 16,
        "train_count_368": len(train) == 368,
        "development_count_64": len(development) == 64,
        "confirmation_count_192": len(confirmation) == 192,
        "registered_training_task_mix": summaries["train"]["task_counts"] == TRAIN_TASKS,
        "all_training_records_fresh": summaries["train"]["source_counts"] == {"FRESH": 368},
        "delayed_evidence_certificate_balance": sorted(json.loads(row["completion"])["decision"] for row in delayed_certificates) == ["ABSTAIN"] * 16 + ["ALLOW"] * 16,
        "delayed_evidence_intervention_weight_18": all(float(row["sample_weight"]) == 18.0 for row in delayed_certificates if row["variant"] == "INTERVENTION"),
        "transition_and_queue_trace_emphasized": summaries["train"]["task_counts"]["TRANSITION"] == summaries["train"]["task_counts"]["QUEUE_TRACE"] == 96,
        "development_task_balance": summaries["development_selection"]["task_counts"] == DEVELOPMENT_TASKS,
        "confirmation_task_balance": summaries["untouched_confirmation"]["task_counts"] == CONFIRMATION_TASKS,
        "splits_case_disjoint": not (case_sets[0] & case_sets[1] or case_sets[0] & case_sets[2] or case_sets[1] & case_sets[2]),
        "splits_pair_disjoint": not (pair_sets[0] & pair_sets[1] or pair_sets[0] & pair_sets[2] or pair_sets[1] & pair_sets[2]),
        "previous_validation_excluded_from_training": data_manifest["dev014_or_dev015_validation_cases_used_for_training"] is False,
        "two_registered_candidates": len(config["development_candidates"]) == 2,
        "deterministic_selection_ranking": config["selection_ranking"] == ["transition_post_state_desc", "certificate_pivotal_desc", "queue_exact_desc", "transition_exact_desc", "pair_exact_desc", "step_asc"],
        "development_rules_ceiling_passes_26": development_rules["full_regression_gate"]["passed"] is True and development_rules["full_regression_gate"]["check_count"] == 26,
        "confirmation_rules_ceiling_passes_26": confirmation_rules["full_regression_gate"]["passed"] is True and confirmation_rules["full_regression_gate"]["check_count"] == 26,
        "confirmation_single_use": config["confirmation_single_use"] is True and data_manifest["confirmation_single_use"] is True,
        "full_regression_confirmation": data_manifest["full_regression_confirmation"] is True,
        "transfer_authorization_disabled": data_manifest["transfer_authorized"] is False,
    }

    adapter = parent_adapter(config)
    parent_manifest_path = parent_artifact_root(config) / "training_manifest.json"
    predictions_path = PARENT / "results" / "development-continuation-step-12-predictions.jsonl"
    step24_predictions = PARENT / "results" / "development-continuation-step-24-predictions.jsonl"
    selection_path = PARENT / "results" / "selected-candidate.json"
    result_path = PARENT / "results" / "dev015-mixed-result.json"
    manifest = read_json(parent_manifest_path) if parent_manifest_path.is_file() else {}
    selection = read_json(selection_path) if selection_path.is_file() else {}
    result = read_json(result_path) if result_path.is_file() else {}
    parent_checks = {
        "parent_adapter_present": adapter.is_dir(),
        "parent_adapter_hash": adapter.is_dir() and sha256_tree(adapter) == config["parent_adapter_tree_sha256"],
        "parent_training_manifest_present": parent_manifest_path.is_file(),
        "parent_training_manifest_identity": manifest.get("protocol_id") == config["parent_protocol"] and manifest.get("continuation_seed") == config["parent_continuation_seed"] and manifest.get("config_sha256") == config["parent_config_sha256"],
        "parent_step12_predictions_present": predictions_path.is_file(),
        "parent_step12_predictions_hash": predictions_path.is_file() and sha256_path(predictions_path) == config["parent_development_predictions_sha256"],
        "parent_step24_predictions_present_for_audit": step24_predictions.is_file(),
        "parent_selection_failed_closed": selection.get("status") == config["parent_development_status"] and selection.get("selected_candidate_id") is None,
        "parent_result_confirmation_sealed": result.get("status") == config["parent_development_status"] and result.get("confirmation_scored") is False,
    }
    if all(parent_checks.values()):
        subprocess.run([sys.executable, "audit_parent.py"], cwd=ROOT, check=True)
    audit_path = ROOT / "results" / "parent-dev015-error-audit.json"
    audit = read_json(audit_path) if audit_path.is_file() else {}
    step12_audit = audit.get("candidate_reports", {}).get("continuation-step-12", {})
    unsafe = step12_audit.get("unsafe_authorizations", [])
    transition_post_state_failures = {
        row.get("case_id")
        for row in step12_audit.get("failures", [])
        if row.get("task_type") == "TRANSITION"
        and any(path == "post_state" or path.startswith("post_state.") for path in row.get("differing_paths", []))
    }
    parent_checks["parent_case_level_audit_complete"] = (
        audit.get("parent_protocol") == "CEREBRUM-DEV-015-MIXED"
        and audit.get("selected_repair_parent") == "continuation-step-12"
        and audit.get("confirmation_accessed") is False
    )
    parent_checks["parent_case_level_failure_signature"] = (
        len(unsafe) == 1
        and unsafe[0].get("intervention_family") == "DELAYED_EVIDENCE"
        and len(transition_post_state_failures) == 2
    )

    core_passed = all(checks.values())
    parent_passed = all(parent_checks.values())
    if core_passed and parent_passed:
        status = "READY_FOR_DEV016_NARROW_GPU_EXECUTION"
    elif core_passed:
        status = "READY_PENDING_DEV015_CHECKPOINT12_IMPORT"
    else:
        status = "DEV016_NARROW_PREFLIGHT_FAILED"
    report = {
        "schema_version": "cerebrum-dev016-narrow-readiness.v1",
        "protocol_id": config["protocol_id"],
        "status": status,
        "core_control_count": len(checks),
        "core_controls_passed": sum(checks.values()),
        "core_controls": checks,
        "parent_control_count": len(parent_checks),
        "parent_controls_passed": sum(parent_checks.values()),
        "parent_controls": parent_checks,
        "expected_optimizer_steps": 12,
        "expected_development_predictions": 128,
        "expected_confirmation_predictions_if_selected": 192,
        "splits": summaries,
        "prepared_hashes": data_manifest["prepared_hashes"],
        "config_sha256": sha256_path(CONFIG),
        "full_regression_confirmation": True,
        "transfer_authorized": False,
        "public_scored": False,
        "binding_authority": False,
        "claim_boundary": "Narrow delayed-evidence and exact-state repair readiness only; no learned checkpoint, confirmation, seed reproducibility, transfer, production, authority, or IGI result.",
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