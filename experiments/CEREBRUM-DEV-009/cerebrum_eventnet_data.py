#!/usr/bin/env python3
"""Prepare fresh ActionNet-009 multi-generator repair targets for CEREBRUM-DEV-009."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parent
ACTIONNET = ROOT.parent / "ACTIONNET-DATA-QUAL-009"
SOURCE_RESULT = "ACTIONNET-DATA-QUAL-009-result-v1.0.0"
REGISTERED_CONDITION_COUNTS = {"multi_generator_execution_repair": 10752}
SYSTEM_PROMPT = (
    "You are Cerebrum, a non-authoritative institutional event-queue repair model. "
    "Use only the supplied observation. Sort events in ascending time, priority, sequence, and event-identifier order. "
    "Execute events at or before the decision clock and defer later events. Apply signed resource deltas, keep approvals "
    "sorted and unique, and preserve the target institution in the authority path. Return exactly the compact JSON schema named in the task "
    "with binding_authority=false. Hashes and changed fields are compiled after generation from predicted "
    "states. Do not add prose, markdown, hidden reasoning, hashes, or metadata."
)


def canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def sha256_path(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def opaque(prefix: str, *parts: Any) -> str:
    payload = ":".join(str(part) for part in parts).encode("utf-8")
    return prefix + "-" + hashlib.sha256(payload).hexdigest()[:20]


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def write_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(canonical(row) + "\n" for row in rows), encoding="utf-8")


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def ensure_actionnet_data(actionnet_root: Path = ACTIONNET) -> None:
    required = (
        actionnet_root / "dataset" / "train.jsonl",
        actionnet_root / "dataset" / "repair_validation.jsonl",
        actionnet_root / "results" / "qualification_report.json",
        actionnet_root / "results" / "result_manifest.json",
        actionnet_root / "oracle" / "reservation.json",
        actionnet_root / "oracle" / "mechanism_catalog.json",
    )
    if all(path.exists() for path in required):
        return
    runner = actionnet_root / "run_campaign.py"
    if not runner.exists():
        raise FileNotFoundError(f"ActionNet v9 runner missing: {runner}")
    overlap_reference = actionnet_root / "oracle" / "actionnet007_overlap_reference.json"
    if not overlap_reference.exists() or overlap_reference.stat().st_size == 0:
        freezer = actionnet_root / "freeze_predecessor_overlap.py"
        if not freezer.exists():
            raise FileNotFoundError(f"ActionNet v9 overlap freezer missing: {freezer}")
        subprocess.run([sys.executable, freezer.name], cwd=actionnet_root, check=True)
    subprocess.run([sys.executable, runner.name], cwd=actionnet_root, check=True)
    missing = [str(path) for path in required if not path.exists()]
    if missing:
        raise FileNotFoundError(f"ActionNet v9 regeneration did not create: {missing}")


def observation_text(observation: dict[str, Any]) -> str:
    media_type = observation["media_type"]
    content = observation["content"]
    if media_type == "application/json;profile=event-queue-pair-v1":
        pair = json.loads(content)
        return (
            f"MEDIA_TYPE={media_type}\n"
            f"BASE_OBSERVATION_BEGIN\n{pair['base_observation']}\nBASE_OBSERVATION_END\n"
            f"COMPARISON_OBSERVATION_BEGIN\n{pair['comparison_observation']}\nCOMPARISON_OBSERVATION_END"
        )
    return f"MEDIA_TYPE={media_type}\n{content}"


def model_prompt(model_input: dict[str, Any]) -> str:
    if set(model_input) != {"observation", "query"}:
        raise ValueError("model input must contain only observation and query")
    return (
        f"SYSTEM\n{SYSTEM_PROMPT}\n\n"
        f"INSTITUTIONAL OBSERVATION\n{observation_text(model_input['observation'])}\n\n"
        f"TASK\n{model_input['query']}\n\nOUTPUT\n"
    )


def model_completion(target: dict[str, Any]) -> str:
    result = dict(target)
    result["binding_authority"] = False
    return canonical(result)


def prepare_row(row: dict[str, Any]) -> dict[str, Any]:
    metadata = row["metadata"]
    prompt = model_prompt(row["input"])
    forbidden_values = (
        row["case_id"],
        metadata.get("trajectory_id"),
        metadata.get("counterfactual_pair_id"),
        metadata.get("institution_lineage"),
        metadata.get("generator_lineage"),
        metadata.get("source_lineage"),
        metadata.get("authority_graph_lineage"),
        metadata.get("workflow_graph_lineage"),
        row["input"]["observation"].get("renderer_lineage"),
    )
    if any(value and str(value) in prompt for value in forbidden_values):
        raise ValueError("audit identifier entered model prompt")
    return {
        "case_id": row["case_id"],
        "prompt": prompt,
        "completion": model_completion(row["target"]),
        "compiler_input": row["input"],
        "sample_weight": float(metadata["sample_weight"]),
        "task_type": metadata["task_type"],
        "pair_class": metadata["pair_class"],
        "variant": metadata["variant"],
        "selected_renderer": metadata["selected_renderer"],
        "counterfactual_pair_id": metadata["counterfactual_pair_id"],
        "intervention_family": metadata.get("intervention_family"),
        "pair_mechanism": metadata.get("pair_mechanism"),
        "semantic_family": metadata["semantic_family"],
        "generator_profile": metadata["generator_profile"],
    }


def condition_rows(train: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    conditions = {"multi_generator_execution_repair": train}
    for name, expected in REGISTERED_CONDITION_COUNTS.items():
        if len(conditions[name]) != expected:
            raise ValueError(f"condition count mismatch for {name}: {len(conditions[name])} != {expected}")
    return conditions


def describe(rows: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "records": len(rows),
        "unique_case_ids": len({row["case_id"] for row in rows}),
        "task_counts": dict(sorted(Counter(row["task_type"] for row in rows).items())),
        "renderer_counts": dict(sorted(Counter(row["selected_renderer"] for row in rows).items())),
        "generator_profile_counts": dict(sorted(Counter(row["generator_profile"] for row in rows).items())),
        "pair_class_counts": dict(sorted(Counter(row["pair_class"] for row in rows).items())),
        "weight_sum": round(sum(float(row["sample_weight"]) for row in rows), 6),
        "weight_min": min(float(row["sample_weight"]) for row in rows),
        "weight_max": max(float(row["sample_weight"]) for row in rows),
        "prompt_chars_max": max(len(row["prompt"]) for row in rows),
        "completion_chars_max": max(len(row["completion"]) for row in rows),
    }


def prepare(actionnet_root: Path = ACTIONNET, output_root: Path | None = None) -> dict[str, Any]:
    output_root = output_root or ROOT / "prepared"
    ensure_actionnet_data(actionnet_root)
    source_report = json.loads((actionnet_root / "results" / "qualification_report.json").read_text(encoding="utf-8"))
    if source_report.get("result_id") != SOURCE_RESULT or source_report.get("status") != "READY_FOR_CEREBRUM_EVENTNET_DEVELOPMENT":
        raise ValueError("ActionNet v9 source is not the frozen qualified multi-generator repair result")
    source_train = read_jsonl(actionnet_root / "dataset" / "train.jsonl")
    source_validation = read_jsonl(actionnet_root / "dataset" / "repair_validation.jsonl")
    train = [prepare_row(row) for row in source_train]
    validation = [prepare_row(row) for row in source_validation]
    conditions = condition_rows(train)
    validation_tasks = {
        "certificate": [row for row in validation if row["task_type"] == "CERTIFICATE"],
        "transition": [row for row in validation if row["task_type"] == "TRANSITION"],
        "queue-trace": [row for row in validation if row["task_type"] == "QUEUE_TRACE"],
        "pair-contrast": [row for row in validation if row["task_type"] == "PAIR_CONTRAST"],
        "all": validation,
    }
    files: dict[str, list[dict[str, Any]]] = {
        "train-execution-repair.jsonl": conditions["multi_generator_execution_repair"],
        "fresh-validation-certificate.jsonl": validation_tasks["certificate"],
        "fresh-validation-transition.jsonl": validation_tasks["transition"],
        "fresh-validation-queue-trace.jsonl": validation_tasks["queue-trace"],
        "fresh-validation-pair-contrast.jsonl": validation_tasks["pair-contrast"],
        "fresh-validation-all.jsonl": validation_tasks["all"],
    }
    for name, rows in files.items():
        write_jsonl(output_root / name, rows)
    source_files = (
        "dataset/train.jsonl",
        "dataset/repair_validation.jsonl",
        "results/qualification_report.json",
        "results/result_manifest.json",
        "oracle/reservation.json",
        "oracle/mechanism_catalog.json",
    )
    manifest = {
        "schema_version": "cerebrum-execution-transfer-repair-data-manifest.v1",
        "protocol_id": "CEREBRUM-DEV-009",
        "source_result": SOURCE_RESULT,
        "source_hashes": {name: sha256_path(actionnet_root / name) for name in source_files},
        "prepared_hashes": {name: sha256_path(output_root / name) for name in files},
        "conditions": {name: describe(rows) for name, rows in conditions.items()},
        "repair_validation": {name: describe(rows) for name, rows in validation_tasks.items()},
        "model_input_fields": ["observation", "query"],
        "renderer_lineage_in_prompts": False,
        "metadata_in_prompts": False,
        "sample_weights_preserved": True,
        "training_generator_profiles": sorted({row["generator_profile"] for row in train}),
        "heldout_validation_generator_profiles": sorted({row["generator_profile"] for row in validation}),
        "queue_trace_supervision": True,
        "compiler_input_excluded_from_model_prompt": True,
        "hash_targets_in_model_completions": False,
        "public_materialized": False,
        "protected_materialized": False,
        "real_institution_materialized": False,
        "transfer007_cases_reused": False,
        "validation_trajectories_with_deferral": sum(
            row["task_type"] == "QUEUE_TRACE" and bool(json.loads(row["completion"])["deferred_event_ids"])
            for row in validation
        ),
        "validation_queue_examples": sum(row["task_type"] == "QUEUE_TRACE" for row in validation),
        "binding_authority": False,
        "claim_boundary": "Fresh-lineage internal synthetic multi-generator repair preparation only; no Transfer-007 case reuse and no public, protected, real-institution, autonomous-authority, or production claim.",
    }
    write_json(output_root / "data_manifest.json", manifest)
    return manifest