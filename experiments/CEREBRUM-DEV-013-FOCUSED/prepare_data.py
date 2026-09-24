#!/usr/bin/env python3
"""Prepare tight near-clock training, selection, and confirmation certificates."""

from __future__ import annotations

import json
from typing import Any

from dev013_common import ACTIONNET, ROOT, canonical, read_json, read_jsonl, sha256_path, summarize, write_json, write_jsonl


SYSTEM_PROMPT = (
    "You are Cerebrum, a non-authoritative institutional event-queue model. Use only the supplied observation. "
    "Sort events by ascending time, priority, sequence, and event identifier. Execute an event if and only if its "
    "time is less than or equal to the decision clock; defer every event whose time is greater than the clock. "
    "For appeal finality, an executed OPEN_APPEAL followed by an executed RESOLVE_APPEAL closes the appeal. A "
    "deferred RESOLVE_APPEAL leaves it unresolved. Treat clock-minus-one and clock-plus-one symmetrically and use "
    "the exact numeric comparison. Return only the exact canonical certificate JSON with binding_authority=false "
    "and no prose, markdown, hidden reasoning, hashes, or metadata."
)


def prepare_row(row: dict[str, Any]) -> dict[str, Any]:
    model_input = row["input"]
    observation = model_input["observation"]
    prompt = (
        f"SYSTEM\n{SYSTEM_PROMPT}\n\nINSTITUTIONAL OBSERVATION\n"
        f"MEDIA_TYPE={observation['media_type']}\n{observation['content']}\n\n"
        f"TASK\n{model_input['query']}\n\nOUTPUT\n"
    )
    metadata = row["metadata"]
    forbidden = [
        row["case_id"], metadata["trajectory_id"], metadata["counterfactual_pair_id"],
        metadata["institution_lineage"], metadata["generator_lineage"], metadata["source_lineage"],
        observation["renderer_lineage"],
    ]
    if any(str(value) in prompt for value in forbidden if value):
        raise ValueError("audit identifier entered model prompt")
    target = dict(row["target"])
    target["binding_authority"] = False
    return {
        "case_id": row["case_id"],
        "prompt": prompt,
        "completion": canonical(target),
        "compiler_input": model_input,
        "sample_weight": float(metadata["sample_weight"]),
        "task_type": "CERTIFICATE",
        "pair_class": metadata["pair_class"],
        "variant": metadata["variant"],
        "selected_renderer": metadata["selected_renderer"],
        "counterfactual_pair_id": metadata["counterfactual_pair_id"],
        "intervention_family": metadata["intervention_family"],
        "pair_mechanism": metadata["pair_mechanism"],
        "semantic_family": metadata["semantic_family"],
        "generator_profile": metadata["generator_profile"],
        "boundary_offset": int(metadata["boundary_offset"]),
        "safety_critical": metadata["safety_critical"],
    }


def prepare() -> dict[str, Any]:
    qualification = read_json(ACTIONNET / "results" / "qualification_report.json")
    if qualification.get("status") != "READY_FOR_CEREBRUM_DEV013_BOUNDARY_SELECTION":
        raise ValueError("ACTIONNET-DATA-QUAL-013 is not qualified")
    sources = {
        "train": ACTIONNET / "dataset" / "train.jsonl",
        "development_selection": ACTIONNET / "dataset" / "development_selection.jsonl",
        "untouched_confirmation": ACTIONNET / "dataset" / "untouched_confirmation.jsonl",
    }
    prepared = {name: [prepare_row(row) for row in read_jsonl(path)] for name, path in sources.items()}
    outputs = {
        "train": ROOT / "prepared" / "train.jsonl",
        "development_selection": ROOT / "prepared" / "development-selection-32.jsonl",
        "untouched_confirmation": ROOT / "prepared" / "untouched-confirmation-64.jsonl",
    }
    for name, rows in prepared.items():
        write_jsonl(outputs[name], rows)
    manifest = {
        "schema_version": "cerebrum-dev013-focused-data-manifest.v1",
        "protocol_id": "CEREBRUM-DEV-013-FOCUSED",
        "source_result": qualification["result_id"],
        "source_hashes": {name: sha256_path(path) for name, path in sources.items()},
        "prepared_hashes": {name: sha256_path(path) for name, path in outputs.items()},
        "splits": {name: summarize(rows) for name, rows in prepared.items()},
        "exact_near_clock_pairs": True,
        "development_selection_is_adaptive": True,
        "confirmation_single_use": True,
        "certificate_only": True,
        "full_regression": False,
        "transfer_authorized": False,
        "binding_authority": False,
    }
    write_json(ROOT / "prepared" / "data-manifest.json", manifest)
    return manifest


if __name__ == "__main__":
    print(json.dumps(prepare(), indent=2, sort_keys=True))
