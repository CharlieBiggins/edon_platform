#!/usr/bin/env python3
"""CPU-safe readiness check for the DEV-009 multi-generator repair protocol."""

from __future__ import annotations

import json

from audit_transfer007 import audit
from canonicalize import compile_prediction, valid_raw
from cerebrum_eventnet_data import ACTIONNET, ROOT, prepare, read_jsonl, sha256_path, write_json, write_jsonl
from evaluate import score
from rules_baseline import predict_input


RESULTS = ROOT / "results"


def main() -> int:
    source_report = json.loads((ACTIONNET / "results" / "qualification_report.json").read_text(encoding="utf-8"))
    observed = json.loads((ROOT / "evidence" / "transfer007-observed-result.json").read_text(encoding="utf-8"))
    failure_audit = audit(observed)
    write_json(RESULTS / "transfer007-failure-audit.json", failure_audit)
    data_manifest = prepare()
    config_path = ROOT / "configs" / "qwen3-4b-multigen-repair.json"
    config = json.loads(config_path.read_text(encoding="utf-8"))
    validation_source = read_jsonl(ACTIONNET / "dataset" / "repair_validation.jsonl")
    prepared_validation = read_jsonl(ROOT / "prepared" / "fresh-validation-all.jsonl")
    prepared_by_id = {row["case_id"]: row for row in prepared_validation}
    predictions = []
    for row in validation_source:
        task = row["metadata"]["task_type"]
        parsed = predict_input(row["input"])
        prepared = prepared_by_id[row["case_id"]]
        predictions.append({
            "case_id": row["case_id"],
            "task_type": task,
            "parsed": parsed,
            "compiled": compile_prediction(task, prepared["compiler_input"], parsed),
            "raw_schema_valid": valid_raw(task, parsed),
            "raw_output": json.dumps(parsed, sort_keys=True),
            "confidence": 1.0,
            "hit_generation_limit": False,
        })
    rules_path = RESULTS / "rules-execution-repair-validation-predictions.jsonl"
    write_jsonl(rules_path, predictions)
    rules_evaluation = score(predictions, prepared_validation, "transparent_rules", None)
    write_json(RESULTS / "rules-execution-repair-validation-evaluation.json", rules_evaluation)

    prepared_full = read_jsonl(ROOT / "prepared" / "train-execution-repair.jsonl")
    train_source = (ROOT / "train_lora.py").read_text(encoding="utf-8")
    predict_source = (ROOT / "predict.py").read_text(encoding="utf-8")
    compiler_source = (ROOT / "canonicalize.py").read_text(encoding="utf-8")
    launcher_source = (ROOT / "lightning_launcher.py").read_text(encoding="utf-8")
    completions = [json.loads(row["completion"]) for row in prepared_full + prepared_validation]
    task_weight_sums = {
        task: sum(float(row["sample_weight"]) for row in prepared_full if row["task_type"] == task)
        for task in config["task_token_limits"]
    }
    controls = {
        "qualified_actionnet_v9_source": source_report.get("status") == "READY_FOR_CEREBRUM_EVENTNET_DEVELOPMENT",
        "source_result_frozen": source_report.get("result_id") == "ACTIONNET-DATA-QUAL-009-result-v1.0.0",
        "registered_condition_count": len(prepared_full) == config["registered_condition_counts"]["multi_generator_execution_repair"] == 10752,
        "fresh_validation_count": len(prepared_validation) == 1344,
        "fresh_validation_task_counts": {
            task: sum(row["task_type"] == task for row in prepared_validation)
            for task in config["task_token_limits"]
        } == {"CERTIFICATE": 384, "TRANSITION": 384, "QUEUE_TRACE": 384, "PAIR_CONTRAST": 192},
        "fresh_validation_renderer": {row["selected_renderer"] for row in prepared_validation} == {"DEPENDENCY_GRAPH_PACKET"},
        "fresh_validation_families": {row["semantic_family"] for row in prepared_validation} == set(range(340, 346)),
        "two_training_generator_profiles": data_manifest["training_generator_profiles"] == ["LEDGER", "MATRIX"],
        "heldout_validation_generator_profile": data_manifest["heldout_validation_generator_profiles"] == ["GRAPH"],
        "transfer007_cases_not_reused": data_manifest["transfer007_cases_reused"] is False,
        "deferral_validation_power": data_manifest["validation_trajectories_with_deferral"] == data_manifest["validation_queue_examples"] == 384,
        "sample_weights_preserved": data_manifest["sample_weights_preserved"] is True and all(row["sample_weight"] > 0 for row in prepared_full),
        "execution_tasks_upweighted": task_weight_sums["QUEUE_TRACE"] > task_weight_sums["TRANSITION"] > task_weight_sums["CERTIFICATE"],
        "pair_diff_supervision_upweighted": task_weight_sums["PAIR_CONTRAST"] > task_weight_sums["CERTIFICATE"],
        "compact_targets_have_no_hash_fields": all("sha256" not in json.dumps(value, sort_keys=True) for value in completions),
        "compiler_input_excluded_from_prompts": all("compiler_input" not in row["prompt"] for row in prepared_full + prepared_validation),
        "deterministic_compiler_present": "def compile_prediction" in compiler_source and "digest(post_state)" in compiler_source and "digest(final_state)" in compiler_source,
        "training_inference_context_match": config["max_length"] == config["inference_max_input_tokens"] == 4096,
        "zero_training_truncation_enforced": config["require_zero_training_truncation"] is True and "zero-truncation protocol violated" in train_source,
        "task_generation_limits_audited": "task_max_completion_tokens" in train_source and "generation_token_margin" in train_source,
        "prediction_limit_hits_recorded": "hit_generation_limit" in predict_source and "generated_token_count" in predict_source,
        "weighted_completion_loss": "class WeightedCompletionTrainer" in train_source and "per_example.float() * weights" in train_source,
        "training_checkpoint_resume": "latest_checkpoint" in launcher_source and "resuming training from" in launcher_source,
        "prediction_checkpoint_resume": "checkpointed_per_case" in predict_source and "prediction progress:" in predict_source,
        "transfer007_failure_audit_confirmed": failure_audit["status"] == "EXECUTION_TRANSFER_FAILURE_CONFIRMED",
        "non_authoritative_targets": all(value.get("binding_authority") is False for value in completions),
        "rules_exact_certificate": rules_evaluation["certificate"]["decision_accuracy"] == 1.0,
        "rules_exact_transition": rules_evaluation["transition"]["exact_match"] == 1.0,
        "rules_exact_queue": rules_evaluation["queue_trace"]["exact_match"] == 1.0,
        "rules_exact_pair": rules_evaluation["pair_contrast"]["exact_match"] == 1.0,
        "rules_pass_repair_gate": rules_evaluation["advancement_gate"]["passed"] is True,
        "two_registered_seeds": config["registered_seeds"] == [26082491, 26082492],
        "no_public_or_protected_launcher_stage": "subparsers.add_parser(\"public\")" not in launcher_source and "subparsers.add_parser(\"protected\")" not in launcher_source,
    }
    ready = all(controls.values())
    report = {
        "schema_version": "cerebrum-execution-transfer-repair-readiness.v1",
        "protocol_id": "CEREBRUM-DEV-009",
        "status": "READY_FOR_RESOURCE_CONTINGENT_EXECUTION" if ready else "BLOCKED_PREFLIGHT_FAILURE",
        "controls": controls,
        "controls_passed": sum(controls.values()),
        "control_count": len(controls),
        "base_model": config["model_name"],
        "primary_condition": config["primary_condition"],
        "registered_seeds": config["registered_seeds"],
        "source_result": source_report["result_id"],
        "rules_diagnostic": rules_evaluation,
        "trained_model_exists": False,
        "resource_contingent": True,
        "public_scored": False,
        "binding_authority": False,
        "claim_boundary": "CPU readiness for a fresh-lineage synthetic multi-generator repair experiment; no learned DEV-009 result yet and no Transfer-007 case reuse.",
    }
    write_json(RESULTS / "readiness_report.json", report)
    artifacts = [
        ROOT / "README.md", ROOT / "PREREGISTRATION.md", ROOT / "MODEL_CARD_TEMPLATE.md",
        ROOT / "FAILURE_AUDIT_PROTOCOL.md", ROOT / "requirements-lightning.txt",
        ROOT / "cerebrum_eventnet_data.py", ROOT / "prepare_data.py", ROOT / "canonicalize.py",
        ROOT / "eventnet_io.py", ROOT / "audit_transfer007.py", ROOT / "train_lora.py", ROOT / "predict.py",
        ROOT / "evaluate.py", ROOT / "summarize_seeds.py", ROOT / "rules_baseline.py",
        ROOT / "hardware_probe.py", ROOT / "lightning_launcher.py", config_path,
        ROOT / "evidence" / "transfer007-observed-result.json", ROOT / "prepared" / "data_manifest.json",
        RESULTS / "transfer007-failure-audit.json",
        RESULTS / "rules-execution-repair-validation-evaluation.json", RESULTS / "readiness_report.json",
    ]
    manifest = {
        "schema_version": "protocol-manifest.v1",
        "protocol_id": "CEREBRUM-DEV-009",
        "status": report["status"],
        "files": {path.relative_to(ROOT).as_posix(): sha256_path(path) for path in artifacts},
        "resource_contingent": True,
        "public_scored": False,
        "claim_boundary": report["claim_boundary"],
    }
    write_json(RESULTS / "protocol_manifest.json", manifest)
    checksum_paths = [
        ROOT / "prepared" / "data_manifest.json",
        RESULTS / "transfer007-failure-audit.json",
        RESULTS / "rules-execution-repair-validation-evaluation.json",
        RESULTS / "readiness_report.json", RESULTS / "protocol_manifest.json",
    ]
    (RESULTS / "checksums.sha256").write_text(
        "\n".join(f"{sha256_path(path)[7:]}  {path.relative_to(ROOT).as_posix()}" for path in checksum_paths) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if ready else 1


if __name__ == "__main__":
    raise SystemExit(main())