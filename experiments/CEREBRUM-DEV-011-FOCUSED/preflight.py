#!/usr/bin/env python3
"""CPU preflight for the two-parent focused continuation protocol."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys

from dev011_common import ACTIONNET, CONFIG, PARENT, ROOT, read_json, read_jsonl, run_spec, sha256_path, summarize, write_json
from prepare_data import prepare
from score import load_evaluator, score_seed


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--allow-missing-parents", action="store_true")
    args = parser.parse_args()
    subprocess.run([sys.executable, "run_campaign.py"], cwd=ACTIONNET, check=True)
    data_manifest = prepare()
    config = read_json(CONFIG)
    qualification = read_json(ACTIONNET / "results" / "qualification_report.json")
    reported = read_json(ROOT / "evidence" / "dev010-operator-reported-result-2026-09-05.json")
    train = read_jsonl(ROOT / "prepared" / "train.jsonl")
    validation = read_jsonl(ROOT / "prepared" / "focused-validation-64.jsonl")
    train_summary = summarize(train)
    validation_summary = summarize(validation)
    evaluator = load_evaluator()
    oracle_predictions = [{
        "case_id": row["case_id"],
        "task_type": "CERTIFICATE",
        "parsed": json.loads(row["completion"]),
        "raw_output": row["completion"],
        "confidence": 1.0,
        "ended_with_eos": True,
        "hit_generation_limit": False,
        "generated_token_count": 1,
        "prompt_token_count": 1,
    } for row in validation]
    oracle = score_seed(validation, oracle_predictions, evaluator, config)
    write_json(ROOT / "results" / "oracle-scoring-ceiling.json", oracle)
    train_pairs = {row["counterfactual_pair_id"] for row in train}
    validation_pairs = {row["counterfactual_pair_id"] for row in validation}
    train_families = {row["semantic_family"] for row in train}
    validation_families = {row["semantic_family"] for row in validation}
    checks = {
        "qualified_source_all_controls": qualification["controls_passed"] == qualification["control_count"],
        "registered_protocol_identity": config["protocol_id"] == "CEREBRUM-DEV-011-FOCUSED",
        "frozen_base_revision": config["model_revision"] == "cdbee75f17c01a7cc42f958dc650907174af0554",
        "two_distinct_parent_runs": [item["parent_seed"] for item in config["registered_runs"]] == [26090401, 26090402],
        "two_fresh_continuation_seeds": [item["continuation_seed"] for item in config["registered_runs"]] == [26090511, 26090512],
        "registered_48_optimizer_steps": config["max_steps"] == 48,
        "low_continuation_learning_rate": config["learning_rate"] == 0.00002,
        "effective_batch_16": config["effective_batch_size"] == 16,
        "train_count_768": len(train) == 768,
        "validation_count_64": len(validation) == 64,
        "certificate_only": (
            train_summary["task_counts"] == {"CERTIFICATE": 768}
            and validation_summary["task_counts"] == {"CERTIFICATE": 64}
        ),
        "balanced_train_decisions": train_summary["decision_counts"] == {"ALLOW": 384, "CONTESTED": 384},
        "balanced_validation_decisions": validation_summary["decision_counts"] == {"ALLOW": 32, "CONTESTED": 32},
        "heldout_renderer_unseen_in_train": set(validation_summary["renderer_counts"]).isdisjoint(train_summary["renderer_counts"]),
        "train_validation_pairs_disjoint": not train_pairs & validation_pairs,
        "train_validation_families_disjoint": not train_families & validation_families,
        "explicit_appeal_clock_prompt": data_manifest["explicit_unresolved_appeal_clock_prompt"] is True,
        "zero_training_truncation_required": config["require_zero_training_truncation"] is True,
        "operator_reported_parent_failure_frozen": (
            reported["status"] == "DEV010_REPAIR_NOT_ESTABLISHED"
            and reported["seeds"]["26090402"]["unsafe_by_intervention_family"] == {"UNRESOLVED_APPEAL": 1}
        ),
        "oracle_scoring_ceiling_passes": oracle["focused_gate"]["passed"] is True,
        "full_regression_disabled": data_manifest["full_regression"] is False,
        "transfer_authorization_disabled": data_manifest["transfer_authorized"] is False,
    }
    parent_checks: dict[str, bool] = {}
    parent_details = []
    for registered in config["registered_runs"]:
        spec = run_spec(config, int(registered["continuation_seed"]))
        parent_seed = int(spec["parent_seed"])
        root = PARENT / "artifacts" / f"dev010-seed-{parent_seed}"
        manifest = root / "training_manifest.json"
        adapter = root / "final-adapter"
        present = manifest.is_file() and adapter.is_dir()
        identity = False
        digest_matches = False
        if present:
            value = read_json(manifest)
            identity = value.get("protocol_id") == "CEREBRUM-DEV-010" and int(value.get("seed", -1)) == parent_seed
            digest_matches = sha256_path(manifest) == spec["parent_training_manifest_sha256"]
        parent_checks[f"parent_{parent_seed}_present"] = present
        parent_checks[f"parent_{parent_seed}_identity"] = identity
        parent_checks[f"parent_{parent_seed}_manifest_hash"] = digest_matches
        parent_details.append({
            "parent_seed": parent_seed,
            "path": root.relative_to(ROOT.parent).as_posix(),
            "present": present,
            "identity_valid": identity,
            "manifest_hash_valid": digest_matches,
        })
    core_passed = all(checks.values())
    parents_passed = all(parent_checks.values())
    if core_passed and parents_passed:
        status = "READY_FOR_TWO_PARENT_FOCUSED_GPU_EXECUTION"
    elif core_passed:
        status = "READY_PENDING_PARENT_ADAPTER_IMPORT"
    else:
        status = "DEV011_FOCUSED_PREFLIGHT_FAILED"
    report = {
        "schema_version": "cerebrum-dev011-focused-readiness.v1",
        "protocol_id": config["protocol_id"],
        "status": status,
        "core_control_count": len(checks),
        "core_controls_passed": sum(checks.values()),
        "core_controls": checks,
        "parent_control_count": len(parent_checks),
        "parent_controls_passed": sum(parent_checks.values()),
        "parent_controls": parent_checks,
        "parent_details": parent_details,
        "expected_optimizer_steps_per_parent": config["max_steps"],
        "train": train_summary,
        "validation": validation_summary,
        "prepared_hashes": data_manifest["prepared_hashes"],
        "config_sha256": sha256_path(CONFIG),
        "full_regression": False,
        "transfer_authorized": False,
        "public_scored": False,
        "binding_authority": False,
        "claim_boundary": "Focused post-failure synthetic readiness only; no learned result, full regression, or transfer authorization.",
    }
    write_json(ROOT / "results" / "readiness-report.json", report)
    print(json.dumps(report, indent=2, sort_keys=True))
    if not core_passed:
        return 1
    if not parents_passed and not args.allow_missing_parents:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())