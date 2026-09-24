#!/usr/bin/env python3
"""Prepare model inputs, scorer records, and answer-key-free verifier inputs."""

from __future__ import annotations

import json
from typing import Any

from dev018_common import ACTIONNET, ROOT, canonical, read_json, read_jsonl, sha256_path, summarize, write_json, write_jsonl


SYSTEM_PROMPT = (
    "You are Cerebrum, a non-authoritative institutional event-queue model. Use only the supplied observation. "
    "Sort every submitted event in ascending time, priority, sequence, and event-identifier order. Every submitted "
    "event identifier must occur exactly once in ordered_event_ids. executed_event_ids and deferred_event_ids must "
    "be disjoint exhaustive order-preserving subsequences: execute time<=decision_clock and defer time>decision_clock. "
    "Apply every executed state mutation exactly. Preserve every field not explicitly targeted by an executed mutation. "
    "Deferred evidence cannot satisfy a current decision, an executed withdrawal removes its approval, and an appeal "
    "is unresolved unless its resolve event executes by the clock. Derive decisions only after reconstructing state. "
    "Return only the exact requested compact JSON with binding_authority=false. Do not add prose or metadata."
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
    expected = dict(row["target"])
    expected["binding_authority"] = False
    return {
        "case_id": row["case_id"],
        "prompt": prompt,
        "completion": canonical(expected),
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


def verifier_row(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "case_id": row["case_id"],
        "task_type": row["task_type"],
        "compiler_input": row["compiler_input"],
    }


def prepare() -> dict[str, Any]:
    qualification = read_json(ACTIONNET / "results" / "qualification_report.json")
    if qualification.get("status") != "READY_FOR_CEREBRUM_DEV018_VERIFIED_HYBRID":
        raise ValueError("ACTIONNET-DATA-QUAL-018 is not qualified")
    sources = {
        "development_selection": ACTIONNET / "dataset" / "development_selection.jsonl",
        "untouched_confirmation": ACTIONNET / "dataset" / "untouched_confirmation.jsonl",
    }
    scorer_outputs = {
        "development_selection": ROOT / "prepared" / "development-selection-64.jsonl",
        "untouched_confirmation": ROOT / "prepared" / "untouched-confirmation-192.jsonl",
    }
    verifier_outputs = {
        "development_selection": ROOT / "prepared" / "development-verifier-inputs-64.jsonl",
        "untouched_confirmation": ROOT / "prepared" / "confirmation-verifier-inputs-192.jsonl",
    }
    prepared = {name: [prepare_row(row) for row in read_jsonl(path)] for name, path in sources.items()}
    for name, rows in prepared.items():
        write_jsonl(scorer_outputs[name], rows)
        write_jsonl(verifier_outputs[name], [verifier_row(row) for row in rows])
    manifest = {
        "schema_version": "cerebrum-dev018-verified-data-manifest.v1",
        "protocol_id": "CEREBRUM-DEV-018-VERIFIED",
        "source_result": qualification["result_id"],
        "source_hashes": {name: sha256_path(path) for name, path in sources.items()},
        "prepared_hashes": {name: sha256_path(path) for name, path in scorer_outputs.items()},
        "verifier_input_hashes": {name: sha256_path(path) for name, path in verifier_outputs.items()},
        "splits": {name: summarize(rows) for name, rows in prepared.items()},
        "training_records": 0,
        "training_authorized": False,
        "verifier_fields": ["case_id", "task_type", "compiler_input"],
        "answer_keys_present_in_verifier_inputs": False,
        "model_and_hybrid_scored_separately": True,
        "confirmation_single_use": True,
        "transfer_authorized": False,
        "binding_authority": False,
    }
    write_json(ROOT / "prepared" / "data-manifest.json", manifest)
    return manifest


if __name__ == "__main__":
    print(json.dumps(prepare(), indent=2, sort_keys=True))