#!/usr/bin/env python3
"""Verify the frozen contribution package and its claim boundaries."""

from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent


def file_hash(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def all_non_binding(value: Any) -> bool:
    if isinstance(value, dict):
        if value.get("binding_authority") is True:
            return False
        return all(all_non_binding(child) for child in value.values())
    if isinstance(value, list):
        return all(all_non_binding(child) for child in value)
    return True


def imported_roots(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    roots = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            roots.update(alias.name.split(".", 1)[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            roots.add(node.module.split(".", 1)[0])
    return roots


def main() -> int:
    required = {
        "README.md", "PROTOCOL.md", "CLAIMS.md", "PREREGISTRATION.md", "RESULT.md",
        "GPU_EXECUTION.md", "build_training.py", "independent_protected_institution.py",
        "proxy_experiment.py", "preflight.py", "train_lora.py", "predict_qwen.py",
        "freeze_qwen_predictions.py", "score_qwen.py",
        "configs/qwen3-4b-platform-contribution.json",
        "training/control.jsonl", "training/platform002.jsonl", "training/manifest.json",
        "protected/public_inputs.jsonl", "protected/labels.jsonl", "protected/manifest.json",
        "results/prediction_freeze.json", "results/proxy_result.json", "results/preflight.json",
    }
    training_manifest = json.loads((ROOT / "training" / "manifest.json").read_text())
    protected_manifest = json.loads((ROOT / "protected" / "manifest.json").read_text())
    proxy = json.loads((ROOT / "results" / "proxy_result.json").read_text())
    freeze = json.loads((ROOT / "results" / "prediction_freeze.json").read_text())
    preflight = json.loads((ROOT / "results" / "preflight.json").read_text())
    config = json.loads((ROOT / "configs" / "qwen3-4b-platform-contribution.json").read_text())
    control = load_jsonl(ROOT / "training" / "control.jsonl")
    active = load_jsonl(ROOT / "training" / "platform002.jsonl")
    public = load_jsonl(ROOT / "protected" / "public_inputs.jsonl")
    labels = load_jsonl(ROOT / "protected" / "labels.jsonl")
    train_ids = {row["record_id"] for row in control + active}
    protected_ids = {row["case_id"] for row in public}
    label_ids = {row["case_id"] for row in labels}
    train_prompt_hashes = {
        hashlib.sha256(row["observation"]["prompt"].encode()).hexdigest()
        for row in control + active
    }
    protected_prompt_hashes = {
        hashlib.sha256(row["observation"]["prompt"].encode()).hexdigest()
        for row in public
    }
    prediction_hashes_valid = all(
        (ROOT / record["path"]).is_file()
        and file_hash(ROOT / record["path"]) == record["prediction_sha256"]
        for record in freeze["predictions"]
    )
    control_origins = {
        row["observation"]["structured"]["experience_origin"] for row in control
    }
    active_origins = {
        row["observation"]["structured"]["experience_origin"] for row in active
    }
    gates = {
        "required_files_present": all((ROOT / path).is_file() for path in required),
        "matched_training_counts": len(control) == len(active) == config["training_records_per_condition"] == 800,
        "training_manifest_hashes_match": (
            file_hash(ROOT / "training" / "control.jsonl") == training_manifest["conditions"]["CONTROL_SINGLE_MECHANISM"]["sha256"]
            and file_hash(ROOT / "training" / "platform002.jsonl") == training_manifest["conditions"]["PLATFORM002_ACTIVE"]["sha256"]
        ),
        "control_contains_only_single_mechanisms": control_origins == {"SINGLE_MECHANISM"},
        "platform002_contains_compositions_and_counterfactuals": {"COMPOSITION", "COUNTERFACTUAL"} <= active_origins,
        "protected_counts_and_identity_match": len(public) == len(labels) == config["protected_cases"] == 320 and protected_ids == label_ids,
        "protected_manifest_hashes_match": (
            file_hash(ROOT / "protected" / "public_inputs.jsonl") == protected_manifest["public_inputs_sha256"]
            and file_hash(ROOT / "protected" / "labels.jsonl") == protected_manifest["protected_labels_sha256"]
        ),
        "protected_labels_separated": protected_manifest["labels_separated"] is True,
        "independent_generator_imports_no_edon_or_actionnet": not ({"edon", "actionnet"} & imported_roots(ROOT / "independent_protected_institution.py")),
        "target_institution_unseen_in_training": all(
            row["observation"]["structured"]["institution_type"] != protected_manifest["target_institution_type"]
            for row in control + active
        ),
        "zero_case_identity_overlap": not (train_ids & protected_ids),
        "zero_prompt_overlap": not (train_prompt_hashes & protected_prompt_hashes),
        "proxy_predictions_frozen": freeze["all_predictions_frozen_before_scoring"] is True and len(freeze["predictions"]) == 4,
        "proxy_prediction_hashes_match": prediction_hashes_valid,
        "proxy_signal_passes_frozen_gates": proxy["status"] == "PROXY_SIGNAL_ESTABLISHED" and all(proxy["gates"].values()),
        "proxy_is_not_mislabeled_cerebrum": proxy["actual_cerebrum_executed"] is False,
        "preflight_records_true_confirmatory_blockers": (
            preflight["status"] == "BLOCKED_MISSING_QWEN_GPU_AND_FRESH_TARGET_CUSTODY"
            and preflight["actual_cerebrum_result_exists"] is False
            and preflight["current_target_confirmatory_eligible"] is False
        ),
        "qwen_conditions_and_seeds_frozen": config["conditions"] == ["control", "platform002"] and config["seeds"] == [26082341, 26082342],
        "qwen_result_absent": not (ROOT / "results" / "qwen_result.json").exists(),
        "qwen_score_receipt_absent": not (ROOT / "results" / "qwen_score_receipt.json").exists(),
        "all_current_records_non_binding": all_non_binding(control + active + public + labels + [proxy, freeze, preflight, config]),
        "training_lineage_denies_protected_exposure": all(
            row["lineage"]["protected_target_exposure"] is False for row in control + active
        ),
    }
    result = {
        "schema_version": "cerebrum-platform-contrib-readiness.v1",
        "experiment_id": "CEREBRUM-PLATFORM-CONTRIB-001",
        "status": "PROXY_SIGNAL_ESTABLISHED_CONFIRMATORY_QWEN_BLOCKED" if all(gates.values()) else "NOT_READY",
        "gates": gates,
        "checks_passed": sum(gates.values()),
        "check_count": len(gates),
        "proxy_status": proxy["status"],
        "qwen_status": "NOT_EXECUTED_BLOCKED_MISSING_QWEN_GPU_AND_FRESH_TARGET_CUSTODY",
        "binding_authority": False,
        "claim_boundary": "Complete proxy contribution diagnostic and Qwen rehearsal; confirmatory Cerebrum claim requires a fresh independently custodied target.",
    }
    (ROOT / "results" / "readiness_report.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if all(gates.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())