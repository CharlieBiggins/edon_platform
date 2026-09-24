#!/usr/bin/env python3
"""Generate native temporal-program supervision for Program-001."""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any

from program_ir import BASE, PARENT, canonical, oracle_program, render_program


ROOT = Path(__file__).resolve().parent
PROTOCOL_ID = "ACTIONNET-DATA-QUAL-021-PROGRAM"
RESULT_ID = "ACTIONNET-DATA-QUAL-021-PROGRAM-result-v1.0.0"
DATASET_ID = "ACTIONNET-NATIVE-TEMPORAL-PROGRAM-v21.0.0"
TRAIN_SEED = 26090741
DEVELOPMENT_SEED = 26090742
CONFIRMATION_SEED = 26090743
TRAIN_FAMILIES = tuple(range(1140, 1268))
DEVELOPMENT_FAMILIES = tuple(range(1280, 1296))
CONFIRMATION_FAMILIES = tuple(range(1320, 1352))
RESERVED_FAMILIES = tuple(range(1380, 1396))
PAIRS_PER_FAMILY = 4


PARENT.PROTOCOL_ID = PROTOCOL_ID
PARENT.PARENT.PROTOCOL_ID = PROTOCOL_ID
PARENT.BASE.PROTOCOL_ID = PROTOCOL_ID
BASE.PROTOCOL_ID = PROTOCOL_ID


def digest(value: Any) -> str:
    payload = value if isinstance(value, bytes) else canonical(value).encode("utf-8")
    return "sha256:" + hashlib.sha256(payload).hexdigest()


def render_familiar_augmented(trajectory: dict[str, Any]) -> tuple[str, str]:
    state = BASE.public_state(trajectory["initial_state"])
    events = trajectory["submitted_events"]
    clock = state["request"]["query_time"]
    content = (
        f"AUGMENTED_DOCKET<{trajectory['domain']}>\n"
        f"INITIAL_RECORD::{canonical(state)}\n"
        f"SCHEDULED_ENTRIES::{' || '.join(BASE.event_text(event) for event in events)}\n"
        f"DISPOSITION_TIME::{clock}\n"
        "ORDER::time,priority,sequence,event_id\n"
        "BOUNDARY::execute at or before disposition time; defer later events"
    )
    return "text/plain;profile=interface-calibration-augmented-docket-v1", content


def renderer_lineage() -> dict[str, Any]:
    return {
        "lineage_id": BASE.opaque("renderer", PROTOCOL_ID, "FAMILIAR_AUGMENTED", "program-v1"),
        "lineage_type": "renderer",
        "version": "1.0.0",
        "content_sha256": digest({"renderer": "FAMILIAR_AUGMENTED", "program": "ACTIONNET_TEMPORAL_PROGRAM_V1"}),
        "parents": [],
        "authority": "EDON Research Lab",
        "transformation": "render-validated-familiar-augmented-program-input-v1",
    }


def make_record(
    trajectory: dict[str, Any], split: str, renderer: dict[str, Any]
) -> dict[str, Any]:
    media_type, content = render_familiar_augmented(trajectory)
    program = oracle_program(trajectory)
    return {
        "case_id": BASE.opaque("program-case", PROTOCOL_ID, split, trajectory["trajectory_id"]),
        "input": {
            "observation": {
                "renderer_lineage": renderer["lineage_id"],
                "media_type": media_type,
                "content": content,
            },
            "query": (
                "Emit one ACTIONNET_TEMPORAL_PROGRAM_V1. List every event exactly once in canonical order, mark "
                "each EXECUTE or DEFER at the disposition boundary, then claim the resulting state and certificate."
            ),
            "program_source": {
                "initial_state": BASE.public_state(trajectory["initial_state"]),
                "submitted_events": trajectory["submitted_events"],
            },
        },
        "target": {
            "program": render_program(program),
            "final_state": program["claim_state"],
            "certificate": program["claim_certificate"],
        },
        "metadata": {
            "trajectory_id": trajectory["trajectory_id"],
            "counterfactual_pair_id": trajectory["counterfactual_pair_id"],
            "pair_class": trajectory["pair_class"],
            "variant": trajectory["variant"],
            "intervention_family": trajectory["intervention_family"],
            "pair_mechanism": trajectory["pair_mechanism"],
            "semantic_family": trajectory["semantic_family"],
            "generator_lineage": trajectory["generator_lineage"],
            "source_lineage": trajectory["source_lineage"],
            "institution_lineage": trajectory["institution_lineage"],
            "authority_graph_lineage": trajectory["authority_graph_lineage"],
            "workflow_graph_lineage": trajectory["workflow_graph_lineage"],
            "selected_renderer": "FAMILIAR_AUGMENTED",
            "task_type": "TEMPORAL_PROGRAM",
            "split": split,
            "decision": trajectory["outcome"]["decision"],
            "sample_weight": 1.0,
            "replay_source_protocol": "FRESH",
        },
    }


def make_split(
    split: str, seed: int, families: tuple[int, ...], domains: tuple[str, ...], renderer: dict[str, Any]
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    trajectories, pairs, lineages, audit = BASE.generate_split(
        split, seed, families, PAIRS_PER_FAMILY, domains, "NATIVE_TEMPORAL_PROGRAM"
    )
    for lineage in lineages:
        if lineage["lineage_type"] == "generator":
            lineage["content_sha256"] = digest({
                "protocol": PROTOCOL_ID,
                "split": split,
                "seed": seed,
                "families": families,
                "implementation": "native-temporal-program-v1",
            })
            lineage["parents"] = ["ACTIONNET-DATA-QUAL-020-result-v1.0.0"]
            lineage["transformation"] = "generate-fresh-native-temporal-program-v1"
    rows = [make_record(trajectory, split, renderer) for trajectory in trajectories]
    return rows, trajectories, pairs, lineages, audit


def summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "records": len(rows),
        "task_counts": dict(sorted(Counter(row["metadata"]["task_type"] for row in rows).items())),
        "decision_counts": dict(sorted(Counter(row["metadata"]["decision"] for row in rows).items())),
        "mechanism_counts": dict(sorted(Counter(row["metadata"]["pair_mechanism"] for row in rows).items())),
        "pair_class_counts": dict(sorted(Counter(row["metadata"]["pair_class"] for row in rows).items())),
    }


def generate() -> dict[str, Any]:
    renderer = renderer_lineage()
    specifications = {
        "train": (TRAIN_SEED, TRAIN_FAMILIES, tuple(f"program-train-{index}" for index in range(16))),
        "development_selection": (
            DEVELOPMENT_SEED,
            DEVELOPMENT_FAMILIES,
            tuple(f"program-development-{index}" for index in range(8)),
        ),
        "untouched_confirmation": (
            CONFIRMATION_SEED,
            CONFIRMATION_FAMILIES,
            tuple(f"program-confirmation-{index}" for index in range(8)),
        ),
    }
    generated = {
        name: make_split(name, seed, families, domains, renderer)
        for name, (seed, families, domains) in specifications.items()
    }
    rows = {name: value[0] for name, value in generated.items()}
    trajectories = {name: value[1] for name, value in generated.items()}
    pairs = {name: value[2] for name, value in generated.items()}
    lineages = [renderer, *(lineage for value in generated.values() for lineage in value[3])]
    audits = {name: value[4] for name, value in generated.items()}
    family_sets = {
        "train": set(TRAIN_FAMILIES),
        "development_selection": set(DEVELOPMENT_FAMILIES),
        "untouched_confirmation": set(CONFIRMATION_FAMILIES),
    }
    case_sets = {name: {row["case_id"] for row in split_rows} for name, split_rows in rows.items()}
    pair_sets = {
        name: {trajectory["counterfactual_pair_id"] for trajectory in split_trajectories}
        for name, split_trajectories in trajectories.items()
    }
    controls = {
        "train_count_1024": len(rows["train"]) == 1024,
        "development_count_128": len(rows["development_selection"]) == 128,
        "confirmation_count_256": len(rows["untouched_confirmation"]) == 256,
        "single_registered_task": all(
            {row["metadata"]["task_type"] for row in split_rows} == {"TEMPORAL_PROGRAM"}
            for split_rows in rows.values()
        ),
        "validated_renderer_only": all(
            row["metadata"]["selected_renderer"] == "FAMILIAR_AUGMENTED"
            for split_rows in rows.values() for row in split_rows
        ),
        "all_records_fresh": all(
            row["metadata"]["replay_source_protocol"] == "FRESH"
            for split_rows in rows.values() for row in split_rows
        ),
        "case_splits_disjoint": not (
            case_sets["train"] & case_sets["development_selection"]
            or case_sets["train"] & case_sets["untouched_confirmation"]
            or case_sets["development_selection"] & case_sets["untouched_confirmation"]
        ),
        "pair_splits_disjoint": not (
            pair_sets["train"] & pair_sets["development_selection"]
            or pair_sets["train"] & pair_sets["untouched_confirmation"]
            or pair_sets["development_selection"] & pair_sets["untouched_confirmation"]
        ),
        "family_splits_disjoint": not (
            family_sets["train"] & family_sets["development_selection"]
            or family_sets["train"] & family_sets["untouched_confirmation"]
            or family_sets["development_selection"] & family_sets["untouched_confirmation"]
        ),
        "dev020_families_excluded": not set(range(1080, 1128)) & set().union(*family_sets.values()),
        "reserved_families_unmaterialized": not set(RESERVED_FAMILIES) & set().union(*family_sets.values()),
        "independent_reference_engines_exact": all(audit["engine_disagreements"] == 0 for audit in audits.values()),
        "independent_schedulers_exact": all(audit["scheduler_disagreements"] == 0 for audit in audits.values()),
        "decision_clock_exact": all(audit["decision_clock_violations"] == 0 for audit in audits.values()),
        "binding_authority_false": all(
            row["target"]["certificate"]["binding_authority"] is False
            for split_rows in rows.values() for row in split_rows
        ),
        "lineage_ids_unique": len({lineage["lineage_id"] for lineage in lineages}) == len(lineages),
    }
    return {
        "schema_version": "actionnet-data-qual-021-program-generated.v1",
        "protocol_id": PROTOCOL_ID,
        "result_id": RESULT_ID,
        "dataset_id": DATASET_ID,
        "rows": rows,
        "trajectories": trajectories,
        "pairs": pairs,
        "lineages": lineages,
        "controls": controls,
        "audits": {**{name: summarize(split_rows) for name, split_rows in rows.items()}, "generator": audits},
        "protected": {
            "confirmation_single_use": True,
            "confirmation_used_for_selection": False,
            "reserved_future_families": list(RESERVED_FAMILIES),
            "public_materialized": False,
            "real_institution_materialized": False,
        },
    }


if __name__ == "__main__":
    generated = generate()
    print(json.dumps({
        "protocol_id": generated["protocol_id"],
        "result_id": generated["result_id"],
        "controls_passed": sum(generated["controls"].values()),
        "control_count": len(generated["controls"]),
        "splits": {name: summarize(rows) for name, rows in generated["rows"].items()},
    }, indent=2, sort_keys=True))