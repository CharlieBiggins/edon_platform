#!/usr/bin/env python3
"""Prepare native temporal-program completion training and evaluation rows."""

from __future__ import annotations

import json
from collections import Counter
from typing import Any

from program_common import ACTIONNET, ROOT, canonical, read_json, read_jsonl, sha256_path, write_json, write_jsonl


SYSTEM_PROMPT = (
    "You are Cerebrum, a non-authoritative institutional temporal-program generator. Use only the supplied "
    "AUGMENTED_DOCKET. Emit exactly ACTIONNET_TEMPORAL_PROGRAM_V1: one STEP compact-JSON line per submitted event "
    "in ascending time, priority, sequence, event_id order; disposition EXECUTE when time is at or before "
    "DISPOSITION_TIME and DEFER otherwise; then one CLAIM_STATE compact-JSON object and one CLAIM_CERTIFICATE "
    "compact-JSON object followed by END_ACTIONNET_TEMPORAL_PROGRAM. Apply executed mutations in step order. "
    "The claimed state must preserve untouched fields and the certificate must be derived from that state with "
    "binding_authority=false. Do not add markdown, prose, hashes, comments, or hidden reasoning."
)


def prepare_row(row: dict[str, Any]) -> dict[str, Any]:
    observation = row["input"]["observation"]
    prompt = (
        f"SYSTEM\n{SYSTEM_PROMPT}\n\nINSTITUTIONAL OBSERVATION\n"
        f"MEDIA_TYPE={observation['media_type']}\n{observation['content']}\n\n"
        f"TASK\n{row['input']['query']}\n\nOUTPUT\n"
    )
    metadata = row["metadata"]
    forbidden = [
        row["case_id"],
        metadata["trajectory_id"],
        metadata["counterfactual_pair_id"],
        metadata["generator_lineage"],
        metadata["source_lineage"],
        metadata["institution_lineage"],
        metadata["authority_graph_lineage"],
        metadata["workflow_graph_lineage"],
        observation["renderer_lineage"],
    ]
    if any(str(value) in prompt for value in forbidden):
        raise ValueError("audit identifier entered Program-001 prompt")
    return {
        "case_id": row["case_id"],
        "prompt": prompt,
        "completion": row["target"]["program"],
        "compiler_input": {
            "program_source": row["input"]["program_source"],
            "oracle_state": row["target"]["final_state"],
            "oracle_certificate": row["target"]["certificate"],
        },
        "sample_weight": float(metadata["sample_weight"]),
        "task_type": "TEMPORAL_PROGRAM",
        "pair_class": metadata["pair_class"],
        "variant": metadata["variant"],
        "counterfactual_pair_id": metadata["counterfactual_pair_id"],
        "pair_mechanism": metadata["pair_mechanism"],
        "intervention_family": metadata["intervention_family"],
        "semantic_family": metadata["semantic_family"],
        "selected_renderer": metadata["selected_renderer"],
        "replay_source_protocol": metadata["replay_source_protocol"],
    }


def summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "records": len(rows),
        "task_counts": dict(sorted(Counter(row["task_type"] for row in rows).items())),
        "mechanism_counts": dict(sorted(Counter(row["pair_mechanism"] for row in rows).items())),
        "renderer_counts": dict(sorted(Counter(row["selected_renderer"] for row in rows).items())),
        "source_counts": dict(sorted(Counter(row["replay_source_protocol"] for row in rows).items())),
    }


def prepare() -> dict[str, Any]:
    qualification = read_json(ACTIONNET / "results" / "qualification_report.json")
    if qualification.get("status") != "READY_FOR_CEREBRUM_END2END_PROGRAM_001":
        raise ValueError("ACTIONNET-DATA-QUAL-021-PROGRAM is not qualified")
    sources = {
        "train": ACTIONNET / "dataset" / "train.jsonl",
        "development_selection": ACTIONNET / "dataset" / "development_selection.jsonl",
        "untouched_confirmation": ACTIONNET / "dataset" / "untouched_confirmation.jsonl",
    }
    outputs = {
        "train": ROOT / "prepared" / "train-1024.jsonl",
        "development_selection": ROOT / "prepared" / "development-selection-128.jsonl",
        "untouched_confirmation": ROOT / "prepared" / "untouched-confirmation-256.jsonl",
    }
    rows = {name: [prepare_row(row) for row in read_jsonl(path)] for name, path in sources.items()}
    for name, split_rows in rows.items():
        write_jsonl(outputs[name], split_rows)
    config_exposures = 16 * 128
    manifest = {
        "schema_version": "cerebrum-program-001-data-manifest.v1",
        "protocol_id": "CEREBRUM-END2END-PROGRAM-001",
        "source_result_id": qualification["result_id"],
        "source_hashes": {name: sha256_path(path) for name, path in sources.items()},
        "prepared_hashes": {name: sha256_path(path) for name, path in outputs.items()},
        "splits": {name: summarize(split_rows) for name, split_rows in rows.items()},
        "training_records": len(rows["train"]),
        "registered_effective_sample_exposures": config_exposures,
        "registered_complete_dataset_passes": config_exposures / len(rows["train"]),
        "fresh_adapter_from_base": True,
        "validated_interface": "FAMILIAR_AUGMENTED",
        "native_program_supervision": True,
        "independent_interpreter_scoring": True,
        "confirmation_single_use": True,
        "transfer_authorized": False,
        "binding_authority": False,
    }
    write_json(ROOT / "prepared" / "data-manifest.json", manifest)
    return manifest


if __name__ == "__main__":
    print(json.dumps(prepare(), indent=2, sort_keys=True))