#!/usr/bin/env python3
"""Prepare fresh narrow-repair training, selection, and confirmation data."""

from __future__ import annotations

import json
from typing import Any

from dev016_common import ACTIONNET, ROOT, canonical, read_json, read_jsonl, sha256_path, summarize, write_json, write_jsonl


SYSTEM_PROMPT = (
    "You are Cerebrum, a non-authoritative institutional event-queue model. Use only the supplied observation. "
    "Sort every submitted event in ascending time, priority, sequence, and event-identifier order. Every submitted "
    "event identifier must occur exactly once in ordered_event_ids. executed_event_ids and deferred_event_ids must "
    "be disjoint exhaustive order-preserving subsequences: execute time<=decision_clock and defer time>decision_clock. "
    "Apply every executed state mutation exactly, including signed resource deltas, approvals, evidence, policy, "
    "routing, conflict, authority, and appeal finality. Never treat an appeal as resolved unless its resolve event "
    "executes at or before the clock. Return only the exact requested compact JSON with binding_authority=false. "
    "Do not add prose, markdown, hidden reasoning, hashes, or metadata."
)


def observation_text(observation: dict[str, Any]) -> str:
    media_type = observation["media_type"]
    content = observation["content"]
    if media_type.startswith("application/json;profile=event-queue-pair"):
        pair = json.loads(content)
        return (
            f"MEDIA_TYPE={media_type}\nBASE_OBSERVATION_BEGIN\n{pair['base_observation']}\nBASE_OBSERVATION_END\n"
            f"COMPARISON_OBSERVATION_BEGIN\n{pair['comparison_observation']}\nCOMPARISON_OBSERVATION_END"
        )
    return f"MEDIA_TYPE={media_type}\n{content}"


def prepare_row(row: dict[str, Any]) -> dict[str, Any]:
    metadata = row["metadata"]
    model_input = row["input"]
    prompt = (
        f"SYSTEM\n{SYSTEM_PROMPT}\n\nINSTITUTIONAL OBSERVATION\n"
        f"{observation_text(model_input['observation'])}\n\nTASK\n{model_input['query']}\n\nOUTPUT\n"
    )
    forbidden = [
        row["case_id"], metadata.get("trajectory_id"), metadata.get("counterfactual_pair_id"),
        metadata.get("institution_lineage"), metadata.get("generator_lineage"), metadata.get("source_lineage"),
        metadata.get("authority_graph_lineage"), metadata.get("workflow_graph_lineage"),
        model_input["observation"].get("renderer_lineage"),
    ]
    if any(value and str(value) in prompt for value in forbidden):
        raise ValueError("audit identifier entered model prompt")
    target = dict(row["target"])
    target["binding_authority"] = False
    return {
        "case_id": row["case_id"],
        "prompt": prompt,
        "completion": canonical(target),
        "compiler_input": model_input,
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
        "replay_source_protocol": metadata.get("replay_source_protocol", "FRESH"),
    }


def prepare() -> dict[str, Any]:
    qualification = read_json(ACTIONNET / "results" / "qualification_report.json")
    if qualification.get("status") != "READY_FOR_CEREBRUM_DEV016_NARROW_REPAIR":
        raise ValueError("ACTIONNET-DATA-QUAL-016 is not qualified")
    sources = {
        "train": ACTIONNET / "dataset" / "train.jsonl",
        "development_selection": ACTIONNET / "dataset" / "development_selection.jsonl",
        "untouched_confirmation": ACTIONNET / "dataset" / "untouched_confirmation.jsonl",
    }
    outputs = {
        "train": ROOT / "prepared" / "train.jsonl",
        "development_selection": ROOT / "prepared" / "development-selection-64.jsonl",
        "untouched_confirmation": ROOT / "prepared" / "untouched-confirmation-192.jsonl",
    }
    prepared = {name: [prepare_row(row) for row in read_jsonl(path)] for name, path in sources.items()}
    for name, rows in prepared.items():
        write_jsonl(outputs[name], rows)
    manifest = {
        "schema_version": "cerebrum-dev016-narrow-data-manifest.v1",
        "protocol_id": "CEREBRUM-DEV-016-NARROW",
        "source_result": qualification["result_id"],
        "source_hashes": {name: sha256_path(path) for name, path in sources.items()},
        "prepared_hashes": {name: sha256_path(path) for name, path in outputs.items()},
        "splits": {name: summarize(rows) for name, rows in prepared.items()},
        "fresh_narrow_repair_training": True,
        "delayed_evidence_safety_emphasis": True,
        "exact_state_reconstruction_emphasis": True,
        "dev014_or_dev015_validation_cases_used_for_training": False,
        "development_selection_is_adaptive": True,
        "confirmation_single_use": True,
        "full_regression_confirmation": True,
        "transfer_authorized": False,
        "binding_authority": False,
    }
    write_json(ROOT / "prepared" / "data-manifest.json", manifest)
    return manifest


if __name__ == "__main__":
    print(json.dumps(prepare(), indent=2, sort_keys=True))