#!/usr/bin/env python3
"""CPU preflight for safety-constrained near-clock checkpoint selection."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys

from dev013_common import ACTIONNET, CONFIG, PARENT, ROOT, candidate_specs, parent_root, read_json, read_jsonl, sha256_path, sha256_tree, summarize, write_json
from prepare_data import prepare
from scoring import load_scorer


def oracle_metrics(rows, scorer, config):
    predictions = [{
        "case_id": row["case_id"],
        "parsed": json.loads(row["completion"]),
        "raw_output": row["completion"],
        "confidence": 1.0,
        "ended_with_eos": True,
        "hit_generation_limit": False,
        "generated_token_count": 1,
        "prompt_token_count": 1,
    } for row in rows]
    return scorer.score_seed(rows, predictions, scorer.load_evaluator(), config)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--allow-missing-parent", action="store_true")
    args = parser.parse_args()
    subprocess.run([sys.executable, "run_campaign.py"], cwd=ACTIONNET, check=True)
    data_manifest = prepare()
    config = read_json(CONFIG)
    qualification = read_json(ACTIONNET / "results" / "qualification_report.json")
    evidence = read_json(ROOT / "evidence" / "operator-reported-dev012-result-2026-09-05.json")
    train = read_jsonl(ROOT / "prepared" / "train.jsonl")
    development = read_jsonl(ROOT / "prepared" / "development-selection-32.jsonl")
    confirmation = read_jsonl(ROOT / "prepared" / "untouched-confirmation-64.jsonl")
    summaries = {name: summarize(rows) for name, rows in {
        "train": train,
        "development_selection": development,
        "untouched_confirmation": confirmation,
    }.items()}
    scorer = load_scorer()
    development_oracle = oracle_metrics(development, scorer, config)
    confirmation_oracle = oracle_metrics(confirmation, scorer, config)
    write_json(ROOT / "results" / "oracle-development-ceiling.json", development_oracle)
    write_json(ROOT / "results" / "oracle-confirmation-ceiling.json", confirmation_oracle)
    pair_sets = [{row["counterfactual_pair_id"] for row in rows} for rows in (train, development, confirmation)]
    family_sets = [{row["semantic_family"] for row in rows} for rows in (train, development, confirmation)]
    renderer_sets = [set(summaries[name]["renderer_counts"]) for name in summaries]
    checks = {
        "qualified_source_all_controls": qualification["controls_passed"] == qualification["control_count"] == 29,
        "registered_protocol_identity": config["protocol_id"] == "CEREBRUM-DEV-013-FOCUSED",
        "frozen_base_revision": config["model_revision"] == "cdbee75f17c01a7cc42f958dc650907174af0554",
        "registered_parent_identity": (
            config["parent_protocol"] == "CEREBRUM-DEV-012-FOCUSED"
            and config["parent_continuation_seed"] == 26090522
            and config["parent_checkpoint_step"] == 12
        ),
        "registered_parent_manifest_hash": config["parent_training_manifest_sha256"] == evidence["training_manifest_sha256"],
        "registered_parent_diagnostic_hash": config["parent_checkpoint_diagnostic_predictions_sha256"] == evidence["step12_diagnostic_predictions_sha256"],
        "operator_reported_learning_curve_frozen": evidence["same_instrument_results"] == [
            {
                "candidate": "DEV-011 parent", "step": 0, "decision_accuracy": 0.59375,
                "resolved_allow_accuracy": 0.1875, "unresolved_contested_accuracy": 1.0,
                "paired_boundary_exact": 0.1875, "unsafe_authorizations": 0,
            },
            {
                "candidate": "DEV-012 checkpoint-12", "step": 12, "decision_accuracy": 0.84375,
                "resolved_allow_accuracy": 0.6875, "unresolved_contested_accuracy": 1.0,
                "paired_boundary_exact": 0.6875, "unsafe_authorizations": 0,
            },
            {
                "candidate": "DEV-012 final checkpoint-24", "step": 24, "decision_accuracy": 0.921875,
                "resolved_allow_accuracy": 0.875, "unresolved_contested_accuracy": 0.96875,
                "paired_boundary_exact": 0.84375, "unsafe_authorizations": 1,
            },
        ],
        "fresh_continuation_seed": config["continuation_seed"] == 26090532,
        "registered_12_optimizer_steps": config["max_steps"] == 12,
        "registered_checkpoints_6_and_12": config["save_steps"] == 6,
        "low_continuation_learning_rate": config["learning_rate"] == 0.000005,
        "effective_batch_16": config["effective_batch_size"] == 16,
        "train_count_192": len(train) == 192,
        "development_count_32": len(development) == 32,
        "confirmation_count_64": len(confirmation) == 64,
        "certificate_only": all(summary["task_counts"] == {"CERTIFICATE": summary["records"]} for summary in summaries.values()),
        "all_splits_balanced": all(summary["decision_counts"] == {"ALLOW": summary["records"] // 2, "CONTESTED": summary["records"] // 2} for summary in summaries.values()),
        "all_splits_tight_offsets": all(summary["boundary_offset_counts"] == {-1: summary["records"] // 2, 1: summary["records"] // 2} for summary in summaries.values()),
        "safety_weighted_training": summaries["train"]["weight_by_decision"] == {"ALLOW": [8.0], "CONTESTED": [9.0]},
        "three_registered_candidates": config["development_candidates"] == [
            {"candidate_id": "parent-step-0", "step": 0},
            {"candidate_id": "continuation-step-6", "step": 6},
            {"candidate_id": "continuation-step-12", "step": 12},
        ],
        "safety_first_selection_gate": (
            config["selection_gate"]["unresolved_contested_accuracy"] == 1.0
            and config["selection_gate"]["unsafe_authorizations_max"] == 0
        ),
        "deterministic_selection_ranking": config["selection_ranking"] == [
            "resolved_allow_accuracy_desc", "paired_boundary_exact_desc", "decision_accuracy_desc", "step_asc"
        ],
        "split_pairs_disjoint": not (pair_sets[0] & pair_sets[1] or pair_sets[0] & pair_sets[2] or pair_sets[1] & pair_sets[2]),
        "split_families_disjoint": not (family_sets[0] & family_sets[1] or family_sets[0] & family_sets[2] or family_sets[1] & family_sets[2]),
        "split_renderers_disjoint": not (renderer_sets[0] & renderer_sets[1] or renderer_sets[0] & renderer_sets[2] or renderer_sets[1] & renderer_sets[2]),
        "oracle_development_ceiling_passes": development_oracle["focused_gate"]["passed"] is True,
        "oracle_confirmation_ceiling_passes": confirmation_oracle["focused_gate"]["passed"] is True,
        "confirmation_single_use": config["confirmation_single_use"] is True and data_manifest["confirmation_single_use"] is True,
        "full_regression_disabled": data_manifest["full_regression"] is False,
        "transfer_authorization_disabled": data_manifest["transfer_authorized"] is False,
    }
    parent = parent_root(config)
    parent_manifest = parent / "training_manifest.json"
    parent_checkpoint = parent / "checkpoint-12"
    diagnostic = PARENT / "results" / "diagnostic-dev012-step12-on-dev012.jsonl"
    diagnostic_manifest = diagnostic.with_suffix(diagnostic.suffix + ".manifest.json")
    manifest_present = parent_manifest.is_file()
    checkpoint_present = parent_checkpoint.is_dir()
    diagnostic_present = diagnostic.is_file() and diagnostic_manifest.is_file()
    manifest_identity = False
    manifest_hash_valid = False
    diagnostic_hash_valid = False
    diagnostic_identity = False
    if manifest_present:
        value = read_json(parent_manifest)
        manifest_identity = (
            value.get("protocol_id") == "CEREBRUM-DEV-012-FOCUSED"
            and int(value.get("continuation_seed", -1)) == config["parent_continuation_seed"]
        )
        manifest_hash_valid = sha256_path(parent_manifest) == config["parent_training_manifest_sha256"]
    if diagnostic_present:
        diagnostic_value = read_json(diagnostic_manifest)
        diagnostic_hash_valid = sha256_path(diagnostic) == config["parent_checkpoint_diagnostic_predictions_sha256"]
        diagnostic_identity = (
            diagnostic_value.get("count") == 64
            and diagnostic_value.get("input_sha256") == config["parent_checkpoint_diagnostic_input_sha256"]
            and str(diagnostic_value.get("adapter", "")).endswith("checkpoint-12")
        )
    parent_checks = {
        "parent_training_manifest_present": manifest_present,
        "parent_training_manifest_identity": manifest_identity,
        "parent_training_manifest_hash": manifest_hash_valid,
        "parent_checkpoint_12_present": checkpoint_present,
        "parent_checkpoint_diagnostic_present": diagnostic_present,
        "parent_checkpoint_diagnostic_hash": diagnostic_hash_valid,
        "parent_checkpoint_diagnostic_identity": diagnostic_identity,
    }
    core_passed = all(checks.values())
    parent_passed = all(parent_checks.values())
    if core_passed and parent_passed:
        status = "READY_FOR_DEV013_SAFETY_CONSTRAINED_GPU_EXECUTION"
    elif core_passed:
        status = "READY_PENDING_DEV012_CHECKPOINT_IMPORT"
    else:
        status = "DEV013_FOCUSED_PREFLIGHT_FAILED"
    report = {
        "schema_version": "cerebrum-dev013-focused-readiness.v1",
        "protocol_id": config["protocol_id"],
        "status": status,
        "core_control_count": len(checks),
        "core_controls_passed": sum(checks.values()),
        "core_controls": checks,
        "parent_control_count": len(parent_checks),
        "parent_controls_passed": sum(parent_checks.values()),
        "parent_controls": parent_checks,
        "parent_checkpoint_tree_sha256": sha256_tree(parent_checkpoint) if checkpoint_present else None,
        "expected_optimizer_steps": config["max_steps"],
        "expected_development_predictions": 96,
        "expected_confirmation_predictions_if_selected": 64,
        "splits": summaries,
        "prepared_hashes": data_manifest["prepared_hashes"],
        "config_sha256": sha256_path(CONFIG),
        "full_regression": False,
        "transfer_authorized": False,
        "public_scored": False,
        "binding_authority": False,
        "claim_boundary": "Safety-constrained near-clock checkpoint selection readiness only; no learned confirmation, full regression, or transfer authorization.",
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
