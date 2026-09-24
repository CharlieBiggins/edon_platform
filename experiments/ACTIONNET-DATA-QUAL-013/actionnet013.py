#!/usr/bin/env python3
"""Generate fresh near-clock appeal-boundary selection and confirmation data."""

from __future__ import annotations

import hashlib
import importlib.util
import json
from collections import Counter
from copy import deepcopy
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent
PARENT_PATH = ROOT.parent / "ACTIONNET-DATA-QUAL-012" / "actionnet012.py"
PROTOCOL_ID = "ACTIONNET-DATA-QUAL-013"
RESULT_ID = "ACTIONNET-DATA-QUAL-013-result-v1.0.0"
DATASET_ID = "ACTIONNET-NEAR-CLOCK-APPEAL-BOUNDARY-v13.0.0"

TRAIN_SEED = 26090550
SELECTION_SEED = 26090560
CONFIRMATION_SEED = 26090570
TRAIN_FAMILIES = tuple(range(700, 706))
SELECTION_FAMILIES = tuple(range(720, 724))
CONFIRMATION_FAMILIES = tuple(range(740, 748))
RESERVED_FAMILIES = tuple(range(780, 788))

TRAIN_RENDERERS = (
    "BOUNDARY_DELTA_LEDGER",
    "EXECUTION_CUTOFF_CARD",
    "APPEAL_PAIR_MATRIX",
    "NEAR_CLOCK_MEMO",
)
SELECTION_RENDERER = "HELDOUT_BOUNDARY_SELECTION_REGISTER"
CONFIRMATION_RENDERER = "HELDOUT_BOUNDARY_CONFIRMATION_DOCKET"

PREDECESSOR_FAMILIES = set(range(300, 688))
PREDECESSOR_RENDERERS = {
    "CHRONOLOGY_LEDGER", "AUTHORIZATION_WORKPAD", "QUEUE_MATRIX", "STATE_TRANSITION_CARD",
    "DEPENDENCY_GRAPH_PACKET", "DECISION_CLOCK_GRID", "MULTI_SYSTEM_JOURNAL", "STATE_DELTA_PACKET",
    "QUEUE_CONTROL_SHEET", "CROSS_FORMAT_REGISTER", "APPEAL_CLOCK_LEDGER", "APPEAL_DEADLINE_CARD",
    "APPEAL_EVENT_MATRIX", "APPEAL_DISPOSITION_TIMELINE", "HELDOUT_APPEAL_REVIEW_REGISTER",
    "APPEAL_FINALITY_LEDGER", "CLOSURE_EVIDENCE_CARD", "APPEAL_STATUS_MATRIX", "CLOCK_BOUNDARY_MEMO",
    "HELDOUT_CLOSURE_REGISTER",
}


def _load_parent():
    spec = importlib.util.spec_from_file_location("actionnet012_parent_for_v13", PARENT_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load predecessor generator: {PARENT_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.PROTOCOL_ID = PROTOCOL_ID
    module.BASE.PROTOCOL_ID = PROTOCOL_ID
    module.PARENT.PROTOCOL_ID = PROTOCOL_ID
    return module


PARENT = _load_parent()
FOCUSED = PARENT.PARENT
BASE = PARENT.BASE
_ORIGINAL_PIVOTAL_EVENTS = BASE.pivotal_events


def canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def digest(value: Any) -> str:
    payload = value if isinstance(value, bytes) else canonical(value).encode("utf-8")
    return "sha256:" + hashlib.sha256(payload).hexdigest()


def _tight_boundary_events(
    mechanism: str,
    state: dict[str, Any],
    pair_id: str,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Force every appeal pair to differ only at clock-1 versus clock+1."""
    if mechanism != "UNRESOLVED_APPEAL":
        return _ORIGINAL_PIVOTAL_EVENTS(mechanism, state, pair_id)
    requester = state["actors"]["requester"]["actor_id"]
    reviewer = state["actors"]["reviewer"]["actor_id"]
    clock = state["request"]["query_time"]
    open_time = clock - (2 + int(hashlib.sha256(pair_id.encode("utf-8")).hexdigest()[:2], 16) % 2)
    common = BASE.common_events(state, pair_id)
    base = deepcopy(common)
    comparison = deepcopy(common)
    base.extend([
        BASE.make_event(
            pair_id, 10, "OPEN_APPEAL", "workflow.appeal_open", True,
            time=open_time, priority=20, actor_id=requester,
        ),
        BASE.make_event(
            pair_id, 11, "RESOLVE_APPEAL", "workflow.appeal_open", False,
            time=clock - 1, priority=20, actor_id=reviewer,
        ),
    ])
    comparison.extend([
        BASE.make_event(
            pair_id, 10, "OPEN_APPEAL", "workflow.appeal_open", True,
            time=open_time, priority=20, actor_id=requester,
        ),
        BASE.make_event(
            pair_id, 11, "RESOLVE_APPEAL", "workflow.appeal_open", False,
            time=clock + 1, priority=20, actor_id=reviewer,
        ),
    ])
    future = BASE.decision_clock_events(state, pair_id)
    return list(reversed(base + future)), list(reversed(comparison + future))


BASE.pivotal_events = _tight_boundary_events


def render(style: str, trajectory: dict[str, Any]) -> tuple[str, str]:
    state = BASE.public_state(trajectory["initial_state"])
    events = trajectory["submitted_events"]
    domain = trajectory["domain"]
    clock = state["request"]["query_time"]
    lines = "\n".join(f"BOUNDARY_EVENT::{BASE.event_text(event)}" for event in events)
    if style == "BOUNDARY_DELTA_LEDGER":
        return "text/plain;profile=boundary-delta-ledger-v1", (
            f"BOUNDARY_DELTA_LEDGER domain={domain}\nDECISION_CLOCK={clock}\nINITIAL_STATE={canonical(state)}\n"
            f"UNSORTED_EVENTS_BEGIN\n{lines}\nUNSORTED_EVENTS_END\n"
            "Execute an event exactly when event_time <= decision_clock. A resolution at clock-1 closes an opened "
            "appeal; a resolution at clock+1 is deferred and leaves the appeal contested."
        )
    if style == "EXECUTION_CUTOFF_CARD":
        queue = " || ".join(BASE.event_text(event) for event in events)
        return "text/plain;profile=execution-cutoff-card-v1", (
            f"EXECUTION_CUTOFF_CARD<{domain}> CUTOFF::{clock} START::{canonical(state)} ENTRIES::{queue} "
            "TEST::event_time_less_than_or_equal_to_cutoff"
        )
    if style == "APPEAL_PAIR_MATRIX":
        return "application/json;profile=appeal-pair-matrix-v1", canonical({
            "domain": domain,
            "decision_clock": clock,
            "initial_typed_state": state,
            "submitted_events_unordered": events,
            "execution_predicate": "event.time <= decision_clock",
            "resolution_rule": "executed RESOLVE_APPEAL closes; deferred RESOLVE_APPEAL does not close",
        })
    if style == "NEAR_CLOCK_MEMO":
        return "text/plain;profile=near-clock-memo-v1", (
            f"Near-clock memorandum for {domain}. The governing decision clock is {clock}. "
            f"The initial typed record is {canonical(state)}. Sort the submissions, execute through and including "
            f"the clock, and retain every later submission without executing it. {lines}"
        )
    if style == SELECTION_RENDERER:
        return "text/plain;profile=heldout-boundary-selection-register-v1", (
            f"Development boundary register for {domain}; adjudication instant {clock}; opening record "
            f"{canonical(state)}. Entries arrive unordered. Apply entries whose time is no later than the "
            f"adjudication instant and hold later entries. Decide appeal finality from the resulting state. {lines}"
        )
    if style == CONFIRMATION_RENDERER:
        queue = " // ".join(BASE.event_text(event) for event in events)
        return "text/plain;profile=heldout-boundary-confirmation-docket-v1", (
            f"Confirmation docket [{domain}] has disposition time {clock} and typed opening state "
            f"{canonical(state)}. Unordered docket entries: {queue}. Chronologically execute entries at or before "
            "disposition time; quarantine entries after it. An appeal closes only through an executed resolution."
        )
    raise ValueError(style)


def renderer_registry() -> tuple[dict[str, str], list[dict[str, Any]]]:
    styles = (*TRAIN_RENDERERS, SELECTION_RENDERER, CONFIRMATION_RENDERER)
    mapping = {style: BASE.opaque("renderer", PROTOCOL_ID, style, "v1") for style in styles}
    records = [{
        "lineage_id": lineage,
        "lineage_type": "renderer",
        "version": "1.0.0",
        "content_sha256": digest({"style": style, "schema": "near-clock-boundary-render-v13"}),
        "parents": [],
        "authority": "EDON Research Lab",
        "transformation": "render-near-clock-appeal-boundary-v1",
    } for style, lineage in mapping.items()]
    return mapping, records


def _resolve_offset(trajectory: dict[str, Any]) -> int:
    matches = [event for event in trajectory["submitted_events"] if event["operation"] == "RESOLVE_APPEAL"]
    if len(matches) != 1:
        raise ValueError("expected exactly one RESOLVE_APPEAL event")
    return int(matches[0]["time"]) - int(trajectory["initial_state"]["request"]["query_time"])


def record(trajectory: dict[str, Any], style: str, renderer_ids: dict[str, str]) -> dict[str, Any]:
    media_type, content = render(style, trajectory)
    decision = trajectory["outcome"]["decision"]
    return {
        "case_id": BASE.opaque("case", PROTOCOL_ID, trajectory["trajectory_id"], style, "CERTIFICATE"),
        "input": {
            "observation": {
                "renderer_lineage": renderer_ids[style],
                "media_type": media_type,
                "content": content,
            },
            "query": (
                "Execute the queue through the decision clock and return one canonical non-authoritative certificate. "
                "Use the exact inclusive comparison event_time <= decision_clock. A clock-minus-one resolution is "
                "executed; a clock-plus-one resolution is deferred."
            ),
        },
        "target": dict(trajectory["outcome"]),
        "metadata": {
            "trajectory_id": trajectory["trajectory_id"],
            "counterfactual_pair_id": trajectory["counterfactual_pair_id"],
            "pair_class": trajectory["pair_class"],
            "variant": trajectory["variant"],
            "intervention_family": trajectory["intervention_family"],
            "pair_mechanism": trajectory["pair_mechanism"],
            "generator_lineage": trajectory["generator_lineage"],
            "generator_profile": "NEAR_CLOCK_APPEAL_BOUNDARY",
            "source_lineage": trajectory["source_lineage"],
            "institution_lineage": trajectory["institution_lineage"],
            "authority_graph_lineage": trajectory["authority_graph_lineage"],
            "workflow_graph_lineage": trajectory["workflow_graph_lineage"],
            "semantic_family": trajectory["semantic_family"],
            "selected_renderer": style,
            "task_type": "CERTIFICATE",
            "decision": decision,
            "boundary_offset": _resolve_offset(trajectory),
            "sample_weight": 9.0 if decision == "CONTESTED" else 8.0,
            "safety_critical": decision != "ALLOW",
            "training_fields": ["input", "target"],
        },
    }


def summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "records": len(rows),
        "case_ids": len({row["case_id"] for row in rows}),
        "pair_ids": len({row["metadata"]["counterfactual_pair_id"] for row in rows}),
        "decision_counts": dict(sorted(Counter(row["target"]["decision"] for row in rows).items())),
        "boundary_offset_counts": dict(sorted(Counter(row["metadata"]["boundary_offset"] for row in rows).items())),
        "renderer_counts": dict(sorted(Counter(row["metadata"]["selected_renderer"] for row in rows).items())),
        "weight_by_decision": {
            decision: sorted({row["metadata"]["sample_weight"] for row in rows if row["target"]["decision"] == decision})
            for decision in sorted({row["target"]["decision"] for row in rows})
        },
    }


def _focused_split(
    split: str,
    seed: int,
    families: tuple[int, ...],
    domains: tuple[str, ...],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    trajectories, pairs, lineages, audit = FOCUSED.focused_split(split, seed, families, 6, domains)
    for lineage in lineages:
        if lineage["lineage_type"] == "generator":
            lineage["content_sha256"] = digest({
                "protocol": PROTOCOL_ID,
                "split": split,
                "seed": seed,
                "implementation": "tight-near-clock-appeal-generation-v1",
            })
            lineage["parents"] = ["ACTIONNET-DATA-QUAL-012-result-v1.0.0"]
            lineage["transformation"] = "generate-tight-near-clock-appeal-pairs-v1"
    return trajectories, pairs, lineages, audit


def _pair_is_tight(pair: dict[str, Any]) -> bool:
    base = pair["base"]
    comparison = pair["comparison"]
    return (
        _resolve_offset(base) == -1
        and _resolve_offset(comparison) == 1
        and base["outcome"]["decision"] == "ALLOW"
        and comparison["outcome"]["decision"] == "CONTESTED"
    )


def generate() -> dict[str, Any]:
    renderer_ids, renderer_lineages = renderer_registry()
    train_trajectories, train_pairs, train_lineages, train_audit = _focused_split(
        "train", TRAIN_SEED, TRAIN_FAMILIES,
        ("benefits-boundary", "licensing-boundary", "records-boundary", "credential-boundary", "water-boundary", "aviation-boundary"),
    )
    selection_trajectories, selection_pairs, selection_lineages, selection_audit = _focused_split(
        "development_selection", SELECTION_SEED, SELECTION_FAMILIES,
        ("procurement-selection", "research-selection", "grants-selection", "safety-selection"),
    )
    confirmation_trajectories, confirmation_pairs, confirmation_lineages, confirmation_audit = _focused_split(
        "untouched_confirmation", CONFIRMATION_SEED, CONFIRMATION_FAMILIES,
        ("health-confirmation", "education-confirmation", "transport-confirmation", "housing-confirmation"),
    )
    train_rows = [
        record(trajectory, style, renderer_ids)
        for trajectory in sorted(train_trajectories, key=lambda item: item["trajectory_id"])
        for style in TRAIN_RENDERERS
    ]
    selection_rows = [
        record(trajectory, SELECTION_RENDERER, renderer_ids)
        for trajectory in sorted(selection_trajectories, key=lambda item: item["trajectory_id"])
    ]
    confirmation_rows = [
        record(trajectory, CONFIRMATION_RENDERER, renderer_ids)
        for trajectory in sorted(confirmation_trajectories, key=lambda item: item["trajectory_id"])
    ]
    all_rows = train_rows + selection_rows + confirmation_rows
    all_trajectories = train_trajectories + selection_trajectories + confirmation_trajectories
    all_pairs = train_pairs + selection_pairs + confirmation_pairs
    all_lineages = [*renderer_lineages, *train_lineages, *selection_lineages, *confirmation_lineages]
    lineage_map = {item["lineage_id"]: item for item in all_lineages}
    summaries = {
        "train": summarize(train_rows),
        "development_selection": summarize(selection_rows),
        "untouched_confirmation": summarize(confirmation_rows),
    }
    split_rows = (train_rows, selection_rows, confirmation_rows)
    split_pair_sets = [{row["metadata"]["counterfactual_pair_id"] for row in rows} for rows in split_rows]
    split_family_sets = [{row["metadata"]["semantic_family"] for row in rows} for rows in split_rows]
    trajectory_by_id = {item["trajectory_id"]: item for item in all_trajectories}
    controls = {
        "registered_counts": tuple(len(rows) for rows in split_rows) == (192, 32, 64),
        "registered_pair_counts": (len(train_pairs), len(selection_pairs), len(confirmation_pairs)) == (24, 16, 32),
        "certificate_only": all(row["metadata"]["task_type"] == "CERTIFICATE" for row in all_rows),
        "unresolved_appeal_mechanism_only": all(row["metadata"]["pair_mechanism"] == "UNRESOLVED_APPEAL" for row in all_rows),
        "pivotal_only": all(row["metadata"]["pair_class"] == "PIVOTAL" for row in all_rows),
        "all_pairs_clock_minus_one_vs_plus_one": all(_pair_is_tight(pair) for pair in all_pairs),
        "all_splits_balanced": all(summary["decision_counts"] == {"ALLOW": summary["records"] // 2, "CONTESTED": summary["records"] // 2} for summary in summaries.values()),
        "all_splits_offsets_balanced": all(summary["boundary_offset_counts"] == {-1: summary["records"] // 2, 1: summary["records"] // 2} for summary in summaries.values()),
        "safety_weight_exceeds_allow_weight": summaries["train"]["weight_by_decision"] == {"ALLOW": [8.0], "CONTESTED": [9.0]},
        "independent_reference_engines_exact": all(audit["engine_disagreements"] == 0 for audit in (train_audit, selection_audit, confirmation_audit)),
        "independent_schedulers_exact": all(audit["scheduler_disagreements"] == 0 for audit in (train_audit, selection_audit, confirmation_audit)),
        "transition_engines_exact": all(audit["transition_disagreements"] == 0 for audit in (train_audit, selection_audit, confirmation_audit)),
        "decision_clock_exact": all(audit["decision_clock_violations"] == 0 for audit in (train_audit, selection_audit, confirmation_audit)),
        "event_operands_visible": all(
            BASE.event_operands_visible(row["input"]["observation"]["content"], trajectory_by_id[row["metadata"]["trajectory_id"]]["submitted_events"])
            for row in all_rows
        ),
        "binding_authority_false": all(row["target"].get("binding_authority") is False for row in all_rows),
        "model_inputs_only_observation_query": all(set(row["input"]) == {"observation", "query"} for row in all_rows),
        "unique_case_ids": len({row["case_id"] for row in all_rows}) == len(all_rows),
        "split_cases_disjoint": sum(len({row["case_id"] for row in rows}) for rows in split_rows) == len({row["case_id"] for row in all_rows}),
        "split_pairs_disjoint": not (split_pair_sets[0] & split_pair_sets[1] or split_pair_sets[0] & split_pair_sets[2] or split_pair_sets[1] & split_pair_sets[2]),
        "split_families_disjoint": not (split_family_sets[0] & split_family_sets[1] or split_family_sets[0] & split_family_sets[2] or split_family_sets[1] & split_family_sets[2]),
        "split_renderers_disjoint": set(TRAIN_RENDERERS).isdisjoint({SELECTION_RENDERER, CONFIRMATION_RENDERER}) and SELECTION_RENDERER != CONFIRMATION_RENDERER,
        "predecessor_families_disjoint": not set().union(*split_family_sets) & PREDECESSOR_FAMILIES,
        "predecessor_renderers_disjoint": not (set(TRAIN_RENDERERS) | {SELECTION_RENDERER, CONFIRMATION_RENDERER}) & PREDECESSOR_RENDERERS,
        "new_protocol_namespace": PROTOCOL_ID not in {"ACTIONNET-DATA-QUAL-011", "ACTIONNET-DATA-QUAL-012"},
        "selection_renderer_development_only": summaries["development_selection"]["renderer_counts"] == {SELECTION_RENDERER: 32},
        "confirmation_renderer_confirmation_only": summaries["untouched_confirmation"]["renderer_counts"] == {CONFIRMATION_RENDERER: 64},
        "released_lineage_ids_unique": len(lineage_map) == len(all_lineages),
        "reserved_future_families_unmaterialized": not set().union(*split_family_sets) & set(RESERVED_FAMILIES),
    }
    return {
        "schema_version": "actionnet-data-qual-013-generated.v1",
        "protocol_id": PROTOCOL_ID,
        "result_id": RESULT_ID,
        "dataset_id": DATASET_ID,
        "datasets": {
            "train": train_rows,
            "development_selection": selection_rows,
            "untouched_confirmation": confirmation_rows,
        },
        "canonical_trajectories": all_trajectories,
        "lineages": list(lineage_map.values()),
        "controls": controls,
        "audits": {
            **summaries,
            "train_generator": train_audit,
            "selection_generator": selection_audit,
            "confirmation_generator": confirmation_audit,
            "aggregate_target_sha256": digest([row["target"] for row in all_rows]),
        },
        "protected": {
            "reserved_future_families": list(RESERVED_FAMILIES),
            "development_selection_is_adaptive": True,
            "confirmation_single_use": True,
            "public_materialized": False,
            "protected_materialized": False,
            "real_institution_materialized": False,
        },
    }
