#!/usr/bin/env python3
"""Prepare balanced ActionNet-012 certificates for short continuation."""

from __future__ import annotations

import json
from typing import Any

from dev012_common import ACTIONNET, ROOT, canonical, read_json, read_jsonl, sha256_path, summarize, write_json, write_jsonl


SYSTEM_PROMPT = (
    "You are Cerebrum, a non-authoritative institutional event-queue model. Use only the supplied observation. "
    "Sort events by ascending time, priority, sequence, and event identifier, execute only events at or before the "
    "decision clock, and defer later events. Determine appeal finality exactly from execution: an OPEN_APPEAL followed "
    "by an executed RESOLVE_APPEAL is closed; if RESOLVE_APPEAL is deferred, the appeal remains unresolved. Apply the "
    "same rule symmetrically without preferring ALLOW or CONTESTED. Return only the exact canonical certificate JSON "
    "with binding_authority=false and no prose, markdown, hidden reasoning, hashes, or metadata."
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
        "safety_critical": metadata["safety_critical"],
    }


def prepare() -> dict[str, Any]:
    qualification = read_json(ACTIONNET / "results" / "qualification_report.json")
    if qualification.get("status") != "READY_FOR_CEREBRUM_DEV012_BALANCE_CONTINUATION":
        raise ValueError("ACTIONNET-DATA-QUAL-012 is not qualified")
    train_source = ACTIONNET / "dataset" / "train.jsonl"
    validation_source = ACTIONNET / "dataset" / "focused_validation.jsonl"
    train = [prepare_row(row) for row in read_jsonl(train_source)]
    validation = [prepare_row(row) for row in read_jsonl(validation_source)]
    train_path = ROOT / "prepared" / "train.jsonl"
    validation_path = ROOT / "prepared" / "focused-validation-64.jsonl"
    write_jsonl(train_path, train)
    write_jsonl(validation_path, validation)
    manifest = {
        "schema_version": "cerebrum-dev012-focused-data-manifest.v1",
        "protocol_id": "CEREBRUM-DEV-012-FOCUSED",
        "source_result": qualification["result_id"],
        "source_hashes": {"train": sha256_path(train_source), "validation": sha256_path(validation_source)},
        "prepared_hashes": {"train": sha256_path(train_path), "validation": sha256_path(validation_path)},
        "train": summarize(train),
        "validation": summarize(validation),
        "symmetric_appeal_finality_prompt": True,
        "symmetric_training_weights": True,
        "certificate_only": True,
        "full_regression": False,
        "transfer_authorized": False,
        "binding_authority": False,
    }
    write_json(ROOT / "prepared" / "data-manifest.json", manifest)
    return manifest


if __name__ == "__main__":
    print(json.dumps(prepare(), indent=2, sort_keys=True))