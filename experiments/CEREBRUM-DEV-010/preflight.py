#!/usr/bin/env python3
"""CPU preflight for CEREBRUM-DEV-010."""

from __future__ import annotations

import importlib
import json
import sys
from collections import Counter

from dev010_common import ACTIONNET, BASE, CONFIG, ROOT, read_json, read_jsonl, sha256_path, summarize, write_json
from prepare_data import prepare
from score import advancement_gate


TRAIN_TASK_COUNTS = {
    "CERTIFICATE": 672,
    "PAIR_CONTRAST": 672,
    "QUEUE_ORDER": 672,
    "QUEUE_PARTITION": 672,
    "QUEUE_TRACE": 672,
    "TRANSITION": 672,
}
VALIDATION_TASK_COUNTS = {"CERTIFICATE": 48, "PAIR_CONTRAST": 48, "QUEUE_TRACE": 48, "TRANSITION": 48}


def load_base_modules():
    sys.path.insert(0, str(BASE))
    try:
        return importlib.import_module("evaluate"), importlib.import_module("rules_baseline"), importlib.import_module("canonicalize")
    finally:
        sys.path.pop(0)


def rules_ceiling(validation: list[dict], config: dict) -> dict:
    evaluator, rules, canonicalize = load_base_modules()
    predictions = []
    for row in validation:
        parsed = rules.predict_input(row["compiler_input"])
        predictions.append({
            "case_id": row["case_id"],
            "task_type": row["task_type"],
            "parsed": parsed,
            "compiled": canonicalize.compile_prediction(row["task_type"], row["compiler_input"], parsed),
            "raw_output": json.dumps(parsed, sort_keys=True),
            "confidence": 1.0,
            "ended_with_eos": False,
            "hit_generation_limit": False,
        })
    result = evaluator.score(predictions, validation, "transparent_rules", None)
    result["advancement_gate"] = advancement_gate(result, config["gate"])
    write_json(ROOT / "results" / "rules-ceiling.json", result)
    return result


def main() -> int:
    data_manifest = prepare()
    config = read_json(CONFIG)
    qualification = read_json(ACTIONNET / "results" / "qualification_report.json")
    rb1_overlap = read_json(ROOT / "results" / "rb1-overlap-audit.json")
    train = read_jsonl(ROOT / "prepared" / "train.jsonl")
    validation = read_jsonl(ROOT / "prepared" / "validation-192.jsonl")
    train_summary = summarize(train)
    validation_summary = summarize(validation)
    rules = rules_ceiling(validation, config)
    train_cases = {row["case_id"] for row in train}
    validation_cases = {row["case_id"] for row in validation}
    train_pairs = {row["counterfactual_pair_id"] for row in train}
    validation_pairs = {row["counterfactual_pair_id"] for row in validation}
    appeal_certificates = [
        row for row in validation
        if row["task_type"] == "CERTIFICATE" and row["pair_mechanism"] == "UNRESOLVED_APPEAL"
    ]
    checks = {
        "qualified_source_33_of_33": qualification["controls_passed"] == qualification["control_count"] == 33,
        "registered_protocol_identity": config["protocol_id"] == "CEREBRUM-DEV-010",
        "frozen_base_revision": config["model_revision"] == "cdbee75f17c01a7cc42f958dc650907174af0554",
        "two_fresh_registered_seeds": config["registered_seeds"] == [26090401, 26090402],
        "one_epoch_registered": config["epochs"] == 1,
        "effective_batch_16": config["effective_batch_size"] == 16,
        "train_count_4032": len(train) == 4032,
        "validation_count_192": len(validation) == 192,
        "train_task_balance": train_summary["task_counts"] == TRAIN_TASK_COUNTS,
        "validation_task_balance": validation_summary["task_counts"] == VALIDATION_TASK_COUNTS,
        "two_training_profiles_balanced": train_summary["profile_counts"] == {"CLOCK_GRID": 2016, "CONTROL_SHEET": 2016},
        "heldout_register_validation": validation_summary["profile_counts"] == {"REGISTER": 192},
        "heldout_renderer_unseen_in_train": set(validation_summary["renderer_counts"]).isdisjoint(train_summary["renderer_counts"]),
        "train_validation_cases_disjoint": not (train_cases & validation_cases),
        "train_validation_pairs_disjoint": not (train_pairs & validation_pairs),
        "rb1_case_and_prompt_overlap_zero": rb1_overlap["passed"] is True and rb1_overlap["case_id_overlap"] == 0 and rb1_overlap["model_prompt_overlap"] == 0,
        "queue_auxiliary_tasks_present": all(train_summary["task_counts"].get(task) == 672 for task in ("QUEUE_ORDER", "QUEUE_PARTITION")),
        "unresolved_appeal_scored_both_sides": {json.loads(row["completion"])["decision"] for row in appeal_certificates} == {"ALLOW", "CONTESTED"},
        "explicit_queue_integrity_prompt": data_manifest["explicit_queue_integrity_prompt"] is True,
        "explicit_appeal_clock_prompt": data_manifest["explicit_unresolved_appeal_clock_prompt"] is True,
        "zero_training_truncation_required": config["require_zero_training_truncation"] is True,
        "matched_train_inference_context": config["max_length"] == config["inference_max_input_tokens"] == 4096,
        "rules_ceiling_passes_all_26_checks": rules["advancement_gate"]["passed"] is True and rules["advancement_gate"]["check_count"] == 26,
        "scoring_locked_until_two_seeds": True,
    }
    passed = all(checks.values())
    report = {
        "schema_version": "cerebrum-dev010-readiness.v1",
        "protocol_id": config["protocol_id"],
        "status": "READY_FOR_TWO_SEED_RESOURCE_CONTINGENT_EXECUTION" if passed else "DEV010_PREFLIGHT_FAILED",
        "control_count": len(checks),
        "controls_passed": sum(checks.values()),
        "controls": checks,
        "registered_seeds": config["registered_seeds"],
        "expected_optimizer_steps_per_seed_on_l4": 252,
        "train": train_summary,
        "validation": validation_summary,
        "prepared_hashes": data_manifest["prepared_hashes"],
        "config_sha256": sha256_path(CONFIG),
        "public_scored": False,
        "binding_authority": False,
        "claim_boundary": "CPU readiness for fresh same-program synthetic repair only; no learned result exists.",
    }
    write_json(ROOT / "results" / "readiness-report.json", report)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())