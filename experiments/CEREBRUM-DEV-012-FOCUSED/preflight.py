#!/usr/bin/env python3
"""CPU preflight for the short balanced appeal-finality continuation."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys

from dev012_common import ACTIONNET, CONFIG, PARENT, ROOT, read_json, read_jsonl, sha256_path, summarize, write_json
from prepare_data import prepare
from score import load_parent_scorer


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--allow-missing-parent", action="store_true")
    args = parser.parse_args()
    subprocess.run([sys.executable, "run_campaign.py"], cwd=ACTIONNET, check=True)
    data_manifest = prepare()
    config = read_json(CONFIG)
    qualification = read_json(ACTIONNET / "results" / "qualification_report.json")
    reported = read_json(ROOT / "evidence" / "dev011-seed-26090512-result.json")
    train = read_jsonl(ROOT / "prepared" / "train.jsonl")
    validation = read_jsonl(ROOT / "prepared" / "focused-validation-64.jsonl")
    train_summary = summarize(train)
    validation_summary = summarize(validation)
    scorer = load_parent_scorer()
    oracle_predictions = [{
        "case_id": row["case_id"],
        "parsed": json.loads(row["completion"]),
        "raw_output": row["completion"],
        "confidence": 1.0,
        "ended_with_eos": True,
        "hit_generation_limit": False,
        "generated_token_count": 1,
        "prompt_token_count": 1,
    } for row in validation]
    oracle = scorer.score_seed(validation, oracle_predictions, scorer.load_evaluator(), config)
    write_json(ROOT / "results" / "oracle-scoring-ceiling.json", oracle)
    train_pairs = {row["counterfactual_pair_id"] for row in train}
    validation_pairs = {row["counterfactual_pair_id"] for row in validation}
    train_families = {row["semantic_family"] for row in train}
    validation_families = {row["semantic_family"] for row in validation}
    checks = {
        "qualified_source_all_controls": qualification["controls_passed"] == qualification["control_count"] == 28,
        "registered_protocol_identity": config["protocol_id"] == "CEREBRUM-DEV-012-FOCUSED",
        "frozen_base_revision": config["model_revision"] == "cdbee75f17c01a7cc42f958dc650907174af0554",
        "registered_parent_identity": (
            config["parent_protocol"] == "CEREBRUM-DEV-011-FOCUSED"
            and config["parent_continuation_seed"] == 26090512
        ),
        "fresh_continuation_seed": config["continuation_seed"] == 26090522,
        "registered_24_optimizer_steps": config["max_steps"] == 24,
        "lower_continuation_learning_rate": config["learning_rate"] == 0.00001,
        "effective_batch_16": config["effective_batch_size"] == 16,
        "train_count_384": len(train) == 384,
        "validation_count_64": len(validation) == 64,
        "certificate_only": (
            train_summary["task_counts"] == {"CERTIFICATE": 384}
            and validation_summary["task_counts"] == {"CERTIFICATE": 64}
        ),
        "balanced_train_decisions": train_summary["decision_counts"] == {"ALLOW": 192, "CONTESTED": 192},
        "balanced_validation_decisions": validation_summary["decision_counts"] == {"ALLOW": 32, "CONTESTED": 32},
        "symmetric_training_weights": train_summary["weight_min"] == train_summary["weight_max"] == 8.0,
        "heldout_renderer_unseen_in_train": set(validation_summary["renderer_counts"]).isdisjoint(train_summary["renderer_counts"]),
        "train_validation_pairs_disjoint": not train_pairs & validation_pairs,
        "train_validation_families_disjoint": not train_families & validation_families,
        "symmetric_finality_prompt": data_manifest["symmetric_appeal_finality_prompt"] is True,
        "operator_reported_parent_near_miss_frozen": (
            reported["status"] == "FOCUSED_REPAIR_HOLD"
            and reported["resolved_allow_accuracy"] == 0.9375
            and reported["unresolved_contested_accuracy"] == 1.0
            and reported["unsafe_authorizations"] == 0
        ),
        "oracle_scoring_ceiling_passes": oracle["focused_gate"]["passed"] is True,
        "full_regression_disabled": data_manifest["full_regression"] is False,
        "transfer_authorization_disabled": data_manifest["transfer_authorized"] is False,
    }
    parent_seed = int(config["parent_continuation_seed"])
    parent_dev010_seed = int(config["parent_dev010_seed"])
    parent_root = PARENT / "artifacts" / f"dev011-parent-{parent_dev010_seed}-seed-{parent_seed}"
    parent_manifest = parent_root / "training_manifest.json"
    parent_adapter = parent_root / "final-adapter"
    present = parent_manifest.is_file() and parent_adapter.is_dir()
    identity = False
    hash_valid = False
    if present:
        value = read_json(parent_manifest)
        identity = (
            value.get("protocol_id") == "CEREBRUM-DEV-011-FOCUSED"
            and int(value.get("continuation_seed", -1)) == parent_seed
        )
        hash_valid = sha256_path(parent_manifest) == config["parent_training_manifest_sha256"]
    parent_checks = {
        "parent_adapter_present": present,
        "parent_identity_valid": identity,
        "parent_manifest_hash_valid": hash_valid,
    }
    core_passed = all(checks.values())
    parent_passed = all(parent_checks.values())
    if core_passed and parent_passed:
        status = "READY_FOR_DEV012_FOCUSED_GPU_EXECUTION"
    elif core_passed:
        status = "READY_PENDING_DEV011_PARENT_IMPORT"
    else:
        status = "DEV012_FOCUSED_PREFLIGHT_FAILED"
    report = {
        "schema_version": "cerebrum-dev012-focused-readiness.v1",
        "protocol_id": config["protocol_id"],
        "status": status,
        "core_control_count": len(checks),
        "core_controls_passed": sum(checks.values()),
        "core_controls": checks,
        "parent_control_count": len(parent_checks),
        "parent_controls_passed": sum(parent_checks.values()),
        "parent_controls": parent_checks,
        "expected_optimizer_steps": config["max_steps"],
        "train": train_summary,
        "validation": validation_summary,
        "prepared_hashes": data_manifest["prepared_hashes"],
        "config_sha256": sha256_path(CONFIG),
        "full_regression": False,
        "transfer_authorized": False,
        "public_scored": False,
        "binding_authority": False,
        "claim_boundary": "Adaptive balanced appeal-finality readiness only; no learned result, full regression, or transfer authorization.",
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