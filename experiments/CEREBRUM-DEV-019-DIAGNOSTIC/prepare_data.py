#!/usr/bin/env python3
"""Prepare the five-condition diagnostic prompts without training artifacts."""

from __future__ import annotations

import json
from collections import Counter

from dev019_common import ACTIONNET, ROOT, canonical, read_json, read_jsonl, sha256_path, write_json, write_jsonl


SYSTEM_PROMPT = (
    "You are Cerebrum, a non-authoritative institutional reasoning model. The diagnostic packet always has the same "
    "schema. Null support fields are unavailable; non-null support fields are oracle-verified and may be used directly. "
    "Use the highest available support level. Apply temporal boundaries exactly, preserve current validity rather than "
    "historical existence, and return only the requested compact certificate JSON with binding_authority=false. "
    "Do not add prose, hashes, metadata, or hidden reasoning."
)


def prepare_row(row: dict) -> dict:
    metadata = row["metadata"]
    packet = row["input"]["observation"]["content"]
    prompt = (
        f"SYSTEM\n{SYSTEM_PROMPT}\n\nDIAGNOSTIC PACKET\n{packet}\n\n"
        f"TASK\n{row['input']['query']}\n\nOUTPUT\n"
    )
    forbidden = [
        row["case_id"],
        metadata.get("diagnostic_scenario_id"),
        metadata.get("trajectory_id"),
        metadata.get("counterfactual_pair_id"),
    ]
    if any(value and str(value) in prompt for value in forbidden):
        raise ValueError("audit identifier entered diagnostic prompt")
    target = dict(row["target"])
    target["binding_authority"] = False
    return {
        "case_id": row["case_id"],
        "prompt": prompt,
        "completion": canonical(target),
        "compiler_input": row["input"],
        "sample_weight": 1.0,
        "task_type": "CERTIFICATE",
        "diagnostic_condition": metadata["diagnostic_condition"],
        "diagnostic_scenario_id": metadata["diagnostic_scenario_id"],
        "pair_class": metadata["pair_class"],
        "variant": metadata["variant"],
        "counterfactual_pair_id": metadata["counterfactual_pair_id"],
        "pair_mechanism": metadata.get("pair_mechanism"),
        "intervention_family": metadata.get("intervention_family"),
        "semantic_family": metadata["semantic_family"],
        "generator_profile": metadata["generator_profile"],
        "selected_renderer": metadata["selected_renderer"],
        "replay_source_protocol": "FRESH",
    }


def prepare() -> dict:
    qualification = read_json(ACTIONNET / "results" / "qualification_report.json")
    if qualification.get("status") != "READY_FOR_CEREBRUM_DEV019_DIAGNOSTIC":
        raise ValueError("ACTIONNET-DATA-QUAL-019 is not qualified")
    source = ACTIONNET / "dataset" / "diagnostic_matrix.jsonl"
    output = ROOT / "prepared" / "diagnostic-matrix-160.jsonl"
    rows = [prepare_row(row) for row in read_jsonl(source)]
    write_jsonl(output, rows)
    conditions = Counter(row["diagnostic_condition"] for row in rows)
    manifest = {
        "schema_version": "cerebrum-dev019-diagnostic-data-manifest.v1",
        "protocol_id": "CEREBRUM-DEV-019-DIAGNOSTIC",
        "source_result": qualification["result_id"],
        "source_sha256": sha256_path(source),
        "prepared_sha256": sha256_path(output),
        "records": len(rows),
        "scenarios": len({row["diagnostic_scenario_id"] for row in rows}),
        "condition_counts": dict(sorted(conditions.items())),
        "training_records": 0,
        "training_authorized": False,
        "repeated_measures": True,
        "targets_identical_within_scenario": all(
            len({row["completion"] for row in rows if row["diagnostic_scenario_id"] == scenario}) == 1
            for scenario in {row["diagnostic_scenario_id"] for row in rows}
        ),
        "dev018_confirmation_reused": False,
        "transfer_authorized": False,
        "binding_authority": False,
    }
    write_json(ROOT / "prepared" / "data-manifest.json", manifest)
    return manifest


if __name__ == "__main__":
    print(json.dumps(prepare(), indent=2, sort_keys=True))