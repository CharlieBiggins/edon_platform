#!/usr/bin/env python3
"""CPU preflight for the complete-exposure causal-chain repair."""

from __future__ import annotations

import argparse
import importlib
import json
import subprocess
import sys
from collections import Counter

from dev017_common import (
    ACTIONNET,
    BASE,
    CONFIG,
    PARENT,
    PREDECESSOR,
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
    "CERTIFICATE": 96,
    "PAIR_CONTRAST": 48,
    "QUEUE_ORDER": 24,
    "QUEUE_PARTITION": 24,
    "QUEUE_TRACE": 96,
    "TRANSITION": 96,
}
DEVELOPMENT_TASKS = {"CERTIFICATE": 16, "PAIR_CONTRAST": 16, "QUEUE_TRACE": 16, "TRANSITION": 16}
CONFIRMATION_TASKS = {"CERTIFICATE": 48, "PAIR_CONTRAST": 48, "QUEUE_TRACE": 48, "TRANSITION": 48}
TARGET_MECHANISMS = {
    "DELAYED_EVIDENCE": 16,
    "APPROVAL_WITHDRAWAL": 12,
    "EVIDENCE_EXPIRY": 8,
    "JURISDICTION_SHIFT": 6,
    "UNRESOLVED_APPEAL": 6,
}


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
    dev015_evidence = read_json(ROOT / "evidence" / "operator-reported-dev015-result-2026-09-06.json")
    dev016_evidence = read_json(ROOT / "evidence" / "operator-reported-dev016-result-2026-09-06.json")

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
    mechanism_pairs = Counter({
        mechanism: len({
            row["counterfactual_pair_id"] for row in train
            if row.get("pair_mechanism") == mechanism
        })
        for mechanism in TARGET_MECHANISMS
    })
    dev015_candidates = {row["candidate_id"]: row for row in dev015_evidence["candidates"]}
    registered_exposures = config["effective_batch_size"] * config["max_steps"]

    checks = {
        "qualified_source_all_controls": qualification["controls_passed"] == qualification["control_count"] == 37,
        "registered_protocol_identity": config["protocol_id"] == "CEREBRUM-DEV-017-CAUSAL",
        "frozen_base_revision": config["model_revision"] == "cdbee75f17c01a7cc42f958dc650907174af0554",
        "registered_training_parent_identity": (
            config["parent_protocol"] == "CEREBRUM-DEV-015-MIXED"
            and config["parent_candidate_id"] == "continuation-step-12"
            and config["parent_checkpoint_step"] == 12
        ),
        "registered_training_parent_hashes": (
            config["parent_adapter_tree_sha256"] == dev015_candidates["continuation-step-12"]["adapter_tree_sha256"]
            and config["parent_development_predictions_sha256"] == dev015_candidates["continuation-step-12"]["predictions_sha256"]
            and config["parent_config_sha256"] == dev015_evidence["config_sha256"]
        ),
        "operator_reported_dev015_hold_frozen": (
            dev015_evidence["status"] == "NO_DEVELOPMENT_CANDIDATE_PASSES_FULL_GATE"
            and dev015_evidence["confirmation_remained_sealed"] is True
        ),
        "operator_reported_dev016_hold_frozen": (
            dev016_evidence["protocol_id"] == config["predecessor_protocol"]
            and dev016_evidence["status"] == config["predecessor_status"]
            and all(row["checks_passed"] == 23 and row["check_count"] == 26 for row in dev016_evidence["candidates"])
        ),
        "operator_reported_dev016_confirmation_sealed": (
            dev016_evidence["confirmation_scored"] is False
            and dev016_evidence["confirmation_remained_sealed"] is True
        ),
        "operator_reported_shared_failure_signature": (
            dev016_evidence["shared_failure_count"] == 12
            and dev016_evidence["failure_counts_by_mechanism"] == {
                "APPROVAL_WITHDRAWAL": 4,
                "DELAYED_EVIDENCE": 5,
                "EVIDENCE_EXPIRY": 1,
                "JURISDICTION_SHIFT": 1,
                "UNRESOLVED_APPEAL": 1,
            }
            and dev016_evidence["failure_counts_by_task"] == {
                "CERTIFICATE": 2,
                "PAIR_CONTRAST": 3,
                "QUEUE_TRACE": 4,
                "TRANSITION": 3,
            }
        ),
        "operator_reported_dev016_underexposure_frozen": (
            dev016_evidence["effective_sample_exposures"] == 192
            and dev016_evidence["training_records"] == 368
            and dev016_evidence["registered_dataset_exposure_fraction"] < 1.0
        ),
        "fresh_continuation_seed": config["continuation_seed"] == 26090642,
        "registered_24_optimizer_steps": config["max_steps"] == 24,
        "registered_checkpoints_12_and_24": (
            config["save_steps"] == 12
            and [row["step"] for row in config["development_candidates"]] == [12, 24]
        ),
        "low_continuation_learning_rate": config["learning_rate"] == 0.000001,
        "effective_batch_16": config["effective_batch_size"] == 16,
        "one_complete_registered_epoch": config["epochs"] == 1 and registered_exposures == len(train) == 384,
        "registered_exposure_count_384": (
            config["registered_effective_sample_exposures"] == registered_exposures == 384
            and data_manifest["registered_full_dataset_exposure"] is True
        ),
        "train_count_384": len(train) == 384,
        "development_count_64": len(development) == 64,
        "confirmation_count_192": len(confirmation) == 192,
        "registered_training_task_mix": summaries["train"]["task_counts"] == TRAIN_TASKS,
        "all_training_records_fresh": summaries["train"]["source_counts"] == {"FRESH": 384},
        "targeted_mechanism_pair_allocation": dict(mechanism_pairs) == TARGET_MECHANISMS,
        "complete_causal_chain_per_pair": qualification["controls"]["complete_causal_chain_per_pair"] is True,
        "mutation_locality_targets": qualification["controls"]["evidence_expiry_mutation_locality_targets"] is True,
        "delayed_evidence_certificate_balance": (
            Counter(json.loads(row["completion"])["decision"] for row in delayed_certificates)
            == {"ALLOW": 16, "ABSTAIN": 16}
        ),
        "transition_and_queue_trace_emphasized": (
            summaries["train"]["task_counts"]["TRANSITION"]
            == summaries["train"]["task_counts"]["QUEUE_TRACE"]
            == 96
        ),
        "three_training_renderers": len(summaries["train"]["renderer_counts"]) == 3,
        "curriculum_order_preserved": data_manifest["curriculum_order_preserved"] is True,
        "development_task_balance": summaries["development_selection"]["task_counts"] == DEVELOPMENT_TASKS,
        "confirmation_task_balance": summaries["untouched_confirmation"]["task_counts"] == CONFIRMATION_TASKS,
        "splits_case_disjoint": not (
            case_sets[0] & case_sets[1] or case_sets[0] & case_sets[2] or case_sets[1] & case_sets[2]
        ),
        "splits_pair_disjoint": not (
            pair_sets[0] & pair_sets[1] or pair_sets[0] & pair_sets[2] or pair_sets[1] & pair_sets[2]
        ),
        "previous_validation_excluded_from_training": (
            data_manifest["dev014_dev015_or_dev016_validation_cases_used_for_training"] is False
        ),
        "two_registered_candidates": len(config["development_candidates"]) == 2,
        "deterministic_selection_ranking": config["selection_ranking"] == [
            "zero_unsafe_authorizations_desc",
            "transition_post_state_desc",
            "certificate_pivotal_desc",
            "queue_exact_desc",
            "transition_exact_desc",
            "pair_exact_desc",
            "step_asc",
        ],
        "development_rules_ceiling_passes_26": (
            development_rules["full_regression_gate"]["passed"] is True
            and development_rules["full_regression_gate"]["check_count"] == 26
        ),
        "confirmation_rules_ceiling_passes_26": (
            confirmation_rules["full_regression_gate"]["passed"] is True
            and confirmation_rules["full_regression_gate"]["check_count"] == 26
        ),
        "confirmation_single_use": (
            config["confirmation_single_use"] is True and data_manifest["confirmation_single_use"] is True
        ),
        "full_regression_confirmation": data_manifest["full_regression_confirmation"] is True,
        "transfer_authorization_disabled": data_manifest["transfer_authorized"] is False,
    }

    adapter = parent_adapter(config)
    parent_manifest_path = parent_artifact_root(config) / "training_manifest.json"
    parent_predictions = PARENT / "results" / "development-continuation-step-12-predictions.jsonl"
    parent_selection_path = PARENT / "results" / "selected-candidate.json"
    parent_result_path = PARENT / "results" / "dev015-mixed-result.json"
    predecessor_expected = PREDECESSOR / "prepared" / "development-selection-64.jsonl"
    predecessor_predictions = {
        row["candidate_id"]: PREDECESSOR / "results" / f"development-{row['candidate_id']}-predictions.jsonl"
        for row in dev016_evidence["candidates"]
    }
    predecessor_selection_path = PREDECESSOR / "results" / "selected-candidate.json"
    predecessor_result_path = PREDECESSOR / "results" / "dev016-narrow-result.json"

    parent_manifest = read_json(parent_manifest_path) if parent_manifest_path.is_file() else {}
    parent_selection = read_json(parent_selection_path) if parent_selection_path.is_file() else {}
    parent_result = read_json(parent_result_path) if parent_result_path.is_file() else {}
    predecessor_selection = read_json(predecessor_selection_path) if predecessor_selection_path.is_file() else {}
    predecessor_result = read_json(predecessor_result_path) if predecessor_result_path.is_file() else {}
    dev016_candidates = {row["candidate_id"]: row for row in dev016_evidence["candidates"]}

    parent_checks = {
        "training_parent_adapter_present": adapter.is_dir(),
        "training_parent_adapter_hash": adapter.is_dir() and sha256_tree(adapter) == config["parent_adapter_tree_sha256"],
        "training_parent_manifest_present": parent_manifest_path.is_file(),
        "training_parent_manifest_identity": (
            parent_manifest.get("protocol_id") == config["parent_protocol"]
            and parent_manifest.get("continuation_seed") == config["parent_continuation_seed"]
            and parent_manifest.get("config_sha256") == config["parent_config_sha256"]
        ),
        "training_parent_predictions_present": parent_predictions.is_file(),
        "training_parent_predictions_hash": (
            parent_predictions.is_file()
            and sha256_path(parent_predictions) == config["parent_development_predictions_sha256"]
        ),
        "training_parent_selection_failed_closed": (
            parent_selection.get("status") == config["parent_development_status"]
            and parent_selection.get("selected_candidate_id") is None
        ),
        "training_parent_result_confirmation_sealed": (
            parent_result.get("status") == config["parent_development_status"]
            and parent_result.get("confirmation_scored") is False
        ),
        "predecessor_development_input_present": predecessor_expected.is_file(),
        "predecessor_candidate_predictions_present": all(path.is_file() for path in predecessor_predictions.values()),
        "predecessor_candidate_prediction_hashes": all(
            path.is_file() and sha256_path(path) == dev016_candidates[candidate_id]["predictions_sha256"]
            for candidate_id, path in predecessor_predictions.items()
        ),
        "predecessor_selection_failed_closed": (
            predecessor_selection.get("status") == config["predecessor_status"]
            and predecessor_selection.get("selected_candidate_id") is None
        ),
        "predecessor_result_confirmation_sealed": (
            predecessor_result.get("status") == config["predecessor_status"]
            and predecessor_result.get("confirmation_scored") is False
        ),
    }

    audit_prerequisites = (
        predecessor_expected.is_file()
        and all(path.is_file() for path in predecessor_predictions.values())
    )
    if audit_prerequisites:
        subprocess.run([sys.executable, "audit_parent.py"], cwd=ROOT, check=True)
    audit_path = ROOT / "results" / "parent-dev016-error-audit.json"
    audit = read_json(audit_path) if audit_path.is_file() else {}
    reports = audit.get("candidate_reports", {})
    expected_unsafe = set(dev016_evidence["unsafe_authorization_case_ids"])
    expected_tasks = dev016_evidence["failure_counts_by_task"]
    expected_mechanisms = dev016_evidence["failure_counts_by_mechanism"]
    report_signatures = []
    for candidate_id in config["predecessor_candidates"]:
        report = reports.get(candidate_id, {})
        failures = report.get("failures", [])
        report_signatures.append(
            report.get("failure_count") == 12
            and report.get("failures_by_task") == expected_tasks
            and Counter(row.get("pair_mechanism") for row in failures) == expected_mechanisms
            and {row["case_id"] for row in report.get("unsafe_authorizations", [])} == expected_unsafe
        )
    parent_checks["predecessor_case_level_audit_complete"] = (
        audit.get("predecessor_protocol") == config["predecessor_protocol"]
        and audit.get("shared_failure_count") == config["predecessor_shared_failure_count"]
        and audit.get("confirmation_accessed") is False
    )
    parent_checks["predecessor_case_level_failure_signature"] = bool(report_signatures) and all(report_signatures)
    parent_checks["predecessor_checkpoint_change_count"] = (
        len(audit.get("compiled_output_changed_case_ids", []))
        == dev016_evidence["changed_output_count_between_checkpoints"]
    )

    core_passed = all(checks.values())
    parent_passed = all(parent_checks.values())
    if core_passed and parent_passed:
        status = "READY_FOR_DEV017_CAUSAL_GPU_EXECUTION"
    elif core_passed:
        status = "READY_PENDING_DEV015_CHECKPOINT12_AND_DEV016_AUDIT_IMPORT"
    else:
        status = "DEV017_CAUSAL_PREFLIGHT_FAILED"

    report = {
        "schema_version": "cerebrum-dev017-causal-readiness.v1",
        "protocol_id": config["protocol_id"],
        "status": status,
        "core_control_count": len(checks),
        "core_controls_passed": sum(checks.values()),
        "core_controls": checks,
        "parent_control_count": len(parent_checks),
        "parent_controls_passed": sum(parent_checks.values()),
        "parent_controls": parent_checks,
        "expected_optimizer_steps": 24,
        "expected_effective_sample_exposures": 384,
        "expected_full_dataset_exposure_fraction": 1.0,
        "expected_development_predictions": 128,
        "expected_confirmation_predictions_if_selected": 192,
        "splits": summaries,
        "prepared_hashes": data_manifest["prepared_hashes"],
        "config_sha256": sha256_path(CONFIG),
        "full_regression_confirmation": True,
        "transfer_authorized": False,
        "public_scored": False,
        "binding_authority": False,
        "claim_boundary": "Complete-exposure causal-chain repair readiness only; no learned checkpoint, confirmation, seed reproducibility, transfer, production, authority, or IGI result.",
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