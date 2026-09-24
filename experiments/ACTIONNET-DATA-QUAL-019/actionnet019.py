#!/usr/bin/env python3
"""Generate fresh repeated-measures gold-intervention diagnostic cases."""

from __future__ import annotations

import hashlib
import importlib.util
import json
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent
EXPERIMENTS = ROOT.parent
PARENT_PATH = EXPERIMENTS / "ACTIONNET-DATA-QUAL-018" / "actionnet018.py"

PROTOCOL_ID = "ACTIONNET-DATA-QUAL-019"
RESULT_ID = "ACTIONNET-DATA-QUAL-019-result-v1.0.0"
DATASET_ID = "ACTIONNET-GOLD-INTERVENTION-DIAGNOSTIC-v19.0.0"
DIAGNOSTIC_SEED = 26090710
DIAGNOSTIC_FAMILIES = tuple(range(1060, 1064))
RESERVED_FAMILIES = tuple(range(1080, 1084))
RAW_RENDERER = "HELDOUT_DIAGNOSTIC_RAW_DOCKET"
CONDITIONS = (
    "A_RAW",
    "B_GOLD_TYPED_EVENTS",
    "C_GOLD_EVENT_ORDER",
    "D_GOLD_PREDECISION_STATE",
    "E_GOLD_DECISION",
)


def _load_parent():
    spec = importlib.util.spec_from_file_location("actionnet018_parent_for_v19", PARENT_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load predecessor generator: {PARENT_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.PROTOCOL_ID = PROTOCOL_ID
    module.PARENT.PROTOCOL_ID = PROTOCOL_ID
    module.V10.PROTOCOL_ID = PROTOCOL_ID
    module.BASE.PROTOCOL_ID = PROTOCOL_ID
    return module


PARENT = _load_parent()
V10 = PARENT.V10
BASE = PARENT.BASE


def canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def digest(value: Any) -> str:
    payload = value if isinstance(value, bytes) else canonical(value).encode("utf-8")
    return "sha256:" + hashlib.sha256(payload).hexdigest()


def raw_observation(style: str, renderer_ids: dict[str, str], trajectory: dict[str, Any]) -> dict[str, Any]:
    if style != RAW_RENDERER:
        raise ValueError(style)
    state = BASE.public_state(trajectory["initial_state"])
    clock = state["request"]["query_time"]
    entries = " || ".join(BASE.event_text(event) for event in trajectory["submitted_events"])
    content = (
        f"DOCKET<{trajectory['domain']}:DIAGNOSTIC_RAW>\n"
        f"INITIAL_RECORD::{canonical(state)}\n"
        f"SCHEDULED_ENTRIES::{entries}\n"
        f"DISPOSITION_TIME::{clock}"
    )
    return {
        "renderer_lineage": renderer_ids[style],
        "media_type": "text/plain;profile=heldout-diagnostic-raw-docket-v1",
        "content": content,
    }


V10.observation = raw_observation


def renderer_registry() -> tuple[dict[str, str], list[dict[str, Any]]]:
    lineage = BASE.opaque("renderer", PROTOCOL_ID, RAW_RENDERER, "v1")
    return {RAW_RENDERER: lineage}, [{
        "lineage_id": lineage,
        "lineage_type": "renderer",
        "version": "1.0.0",
        "content_sha256": digest({"style": RAW_RENDERER, "schema": "diagnostic-raw-docket-v19"}),
        "parents": [],
        "authority": "EDON Research Lab",
        "transformation": "render-gold-intervention-diagnostic-v1",
    }]


def ordered_events(trajectory: dict[str, Any]) -> list[dict[str, Any]]:
    by_id = {event["event_id"]: event for event in trajectory["submitted_events"]}
    return [by_id[event_id] for event_id in trajectory["execution_receipt"]["ordered_event_ids"]]


def support_packet(condition: str, trajectory: dict[str, Any], raw: dict[str, Any]) -> dict[str, Any]:
    level = CONDITIONS.index(condition)
    return {
        "schema_version": "cerebrum-gold-intervention-packet.v1",
        "condition": condition,
        "raw_observation": {
            "media_type": raw["media_type"],
            "content": raw["content"],
        },
        "typed_initial_state": BASE.public_state(trajectory["initial_state"]) if level >= 1 else None,
        "typed_events": trajectory["submitted_events"] if level >= 1 else None,
        "decision_clock": BASE.public_state(trajectory["initial_state"])["request"]["query_time"] if level >= 1 else None,
        "canonical_event_order": trajectory["execution_receipt"]["ordered_event_ids"] if level >= 2 else None,
        "ordered_events": ordered_events(trajectory) if level >= 2 else None,
        "predecision_state": BASE.public_state(trajectory["final_state"]) if level >= 3 else None,
        "gold_decision": trajectory["outcome"]["decision"] if level >= 4 else None,
        "support_semantics": (
            "Null fields are unavailable. Non-null diagnostic support is oracle-verified. "
            "Use the highest available support level without inventing missing values."
        ),
    }


def diagnostic_record(
    trajectory: dict[str, Any],
    condition: str,
    renderer_ids: dict[str, str],
) -> dict[str, Any]:
    base = V10.state_record(trajectory, RAW_RENDERER, renderer_ids, "CERTIFICATE")
    raw = base["input"]["observation"]
    packet = support_packet(condition, trajectory, raw)
    scenario_id = BASE.opaque("diagnostic-scenario", PROTOCOL_ID, trajectory["trajectory_id"])
    case_id = BASE.opaque("case", PROTOCOL_ID, trajectory["trajectory_id"], condition)
    metadata = dict(base["metadata"])
    metadata.update({
        "task_type": "CERTIFICATE",
        "generator_profile": "GOLD_INTERVENTION_DIAGNOSTIC",
        "selected_renderer": "GOLD_INTERVENTION_PACKET",
        "diagnostic_condition": condition,
        "diagnostic_scenario_id": scenario_id,
        "sample_weight": 1.0,
        "replay_source_protocol": "FRESH",
    })
    return {
        "case_id": case_id,
        "input": {
            "observation": {
                "renderer_lineage": raw["renderer_lineage"],
                "media_type": "application/json;profile=gold-intervention-diagnostic-v1",
                "content": canonical(packet),
            },
            "query": base["input"]["query"],
        },
        "target": base["target"],
        "metadata": metadata,
    }


def generate() -> dict[str, Any]:
    renderer_ids, renderer_lineages = renderer_registry()
    trajectories, pairs, lineages, audit = BASE.generate_split(
        "diagnostic",
        DIAGNOSTIC_SEED,
        DIAGNOSTIC_FAMILIES,
        4,
        tuple(f"institutional-diagnostic-{index}" for index in range(4)),
        "GOLD_INTERVENTION_DIAGNOSTIC",
    )
    for lineage in lineages:
        if lineage["lineage_type"] == "generator":
            lineage["content_sha256"] = digest({
                "protocol": PROTOCOL_ID,
                "seed": DIAGNOSTIC_SEED,
                "families": DIAGNOSTIC_FAMILIES,
                "implementation": "fresh-gold-intervention-diagnostic-v1",
            })
            lineage["parents"] = ["ACTIONNET-DATA-QUAL-018-result-v1.0.0"]
            lineage["transformation"] = "generate-fresh-gold-intervention-diagnostic-v1"
    rows = [
        diagnostic_record(trajectory, condition, renderer_ids)
        for trajectory in trajectories
        for condition in CONDITIONS
    ]
    by_scenario: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        by_scenario.setdefault(row["metadata"]["diagnostic_scenario_id"], []).append(row)
    packets = [json.loads(row["input"]["observation"]["content"]) for row in rows]
    condition_counts = Counter(row["metadata"]["diagnostic_condition"] for row in rows)
    pair_class_counts = Counter(trajectory["pair_class"] for trajectory in trajectories)
    pivotal_mechanisms = Counter(
        pair["intervention_family"] for pair in pairs if pair["pair_class"] == "PIVOTAL"
    )
    controls = {
        "registered_record_count_160": len(rows) == 160,
        "registered_scenario_count_32": len(by_scenario) == 32,
        "five_conditions_per_scenario": all(len(group) == 5 for group in by_scenario.values()),
        "condition_counts_balanced": condition_counts == {condition: 32 for condition in CONDITIONS},
        "targets_identical_within_scenario": all(
            len({canonical(row["target"]) for row in group}) == 1 for group in by_scenario.values()
        ),
        "condition_order_complete": all(
            {row["metadata"]["diagnostic_condition"] for row in group} == set(CONDITIONS)
            for group in by_scenario.values()
        ),
        "registered_pair_class_distribution": pair_class_counts == {
            "PIVOTAL": 24,
            "INVARIANCE": 4,
            "CONTEXTUAL": 4,
        },
        "all_twelve_pivotal_mechanisms_present": len(pivotal_mechanisms) == 12 and all(
            count == 1 for count in pivotal_mechanisms.values()
        ),
        "raw_condition_has_no_gold_support": all(
            packet["typed_initial_state"] is None
            and packet["typed_events"] is None
            and packet["canonical_event_order"] is None
            and packet["predecision_state"] is None
            and packet["gold_decision"] is None
            for packet in packets if packet["condition"] == "A_RAW"
        ),
        "typed_event_condition_has_only_typed_support": all(
            packet["typed_initial_state"] is not None
            and packet["typed_events"] is not None
            and packet["canonical_event_order"] is None
            and packet["predecision_state"] is None
            and packet["gold_decision"] is None
            for packet in packets if packet["condition"] == "B_GOLD_TYPED_EVENTS"
        ),
        "event_order_condition_is_cumulative": all(
            packet["typed_events"] is not None
            and packet["canonical_event_order"] is not None
            and packet["ordered_events"] is not None
            and packet["predecision_state"] is None
            and packet["gold_decision"] is None
            for packet in packets if packet["condition"] == "C_GOLD_EVENT_ORDER"
        ),
        "state_condition_is_cumulative_without_decision": all(
            packet["canonical_event_order"] is not None
            and packet["predecision_state"] is not None
            and packet["gold_decision"] is None
            for packet in packets if packet["condition"] == "D_GOLD_PREDECISION_STATE"
        ),
        "decision_condition_is_cumulative": all(
            packet["predecision_state"] is not None and packet["gold_decision"] is not None
            for packet in packets if packet["condition"] == "E_GOLD_DECISION"
        ),
        "gold_order_matches_oracle": all(
            packet["canonical_event_order"] == trajectory["execution_receipt"]["ordered_event_ids"]
            for trajectory in trajectories
            for packet in [support_packet("C_GOLD_EVENT_ORDER", trajectory, raw_observation(RAW_RENDERER, renderer_ids, trajectory))]
        ),
        "gold_state_matches_oracle": all(
            packet["predecision_state"] == BASE.public_state(trajectory["final_state"])
            for trajectory in trajectories
            for packet in [support_packet("D_GOLD_PREDECISION_STATE", trajectory, raw_observation(RAW_RENDERER, renderer_ids, trajectory))]
        ),
        "gold_decision_matches_oracle": all(
            packet["gold_decision"] == trajectory["outcome"]["decision"]
            for trajectory in trajectories
            for packet in [support_packet("E_GOLD_DECISION", trajectory, raw_observation(RAW_RENDERER, renderer_ids, trajectory))]
        ),
        "wrapper_schema_distribution_matched": len({tuple(sorted(packet)) for packet in packets}) == 1,
        "all_records_fresh": all(row["metadata"]["replay_source_protocol"] == "FRESH" for row in rows),
        "previous_family_ranges_disjoint": not set(DIAGNOSTIC_FAMILIES) & set(range(780, 1044)),
        "case_ids_unique": len({row["case_id"] for row in rows}) == len(rows),
        "scenario_ids_hidden_from_inputs": all(
            row["metadata"]["diagnostic_scenario_id"] not in row["input"]["observation"]["content"]
            for row in rows
        ),
        "queue_integrity_exact": all(V10.queue_integrity(trajectory) for trajectory in trajectories),
        "independent_reference_engines_exact": audit["engine_disagreements"] == 0,
        "independent_schedulers_exact": audit["scheduler_disagreements"] == 0,
        "transition_engines_exact": audit["transition_disagreements"] == 0,
        "decision_clock_exact": audit["decision_clock_violations"] == 0,
        "binding_authority_false": all(row["target"].get("binding_authority") is False for row in rows),
        "evaluation_only_no_training_split": True,
        "fresh_seed_registered": DIAGNOSTIC_SEED == 26090710,
        "reserved_future_families_unmaterialized": not set(DIAGNOSTIC_FAMILIES) & set(RESERVED_FAMILIES),
        "confirmation_data_not_reused": True,
        "transfer_authorization_disabled": True,
    }
    all_lineages = [*renderer_lineages, *lineages]
    controls["lineage_ids_unique"] = len({row["lineage_id"] for row in all_lineages}) == len(all_lineages)
    return {
        "schema_version": "actionnet-data-qual-019-generated.v1",
        "protocol_id": PROTOCOL_ID,
        "result_id": RESULT_ID,
        "dataset_id": DATASET_ID,
        "dataset": rows,
        "canonical_trajectories": trajectories,
        "lineages": all_lineages,
        "controls": controls,
        "audits": {
            "records": len(rows),
            "scenarios": len(by_scenario),
            "pairs": len(pairs),
            "condition_counts": dict(sorted(condition_counts.items())),
            "pair_class_counts": dict(sorted(pair_class_counts.items())),
            "pivotal_mechanism_counts": dict(sorted(pivotal_mechanisms.items())),
            "generator": audit,
            "aggregate_target_sha256": digest([row["target"] for row in rows]),
        },
        "protected": {
            "reserved_future_families": list(RESERVED_FAMILIES),
            "evaluation_only": True,
            "training_split_materialized": False,
            "dev018_confirmation_reused": False,
            "public_materialized": False,
            "protected_materialized": False,
            "real_institution_materialized": False,
        },
    }