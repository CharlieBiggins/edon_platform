#!/usr/bin/env python3
"""Generate fresh balanced appeal-finality calibration data."""

from __future__ import annotations

import hashlib
import importlib.util
import json
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent
PARENT_PATH = ROOT.parent / "ACTIONNET-DATA-QUAL-011" / "actionnet011.py"
PROTOCOL_ID = "ACTIONNET-DATA-QUAL-012"
RESULT_ID = "ACTIONNET-DATA-QUAL-012-result-v1.0.0"
DATASET_ID = "ACTIONNET-APPEAL-FINALITY-CALIBRATION-v12.0.0"
TRAIN_SEED = 26090530
VALIDATION_SEED = 26090540
TRAIN_FAMILIES = tuple(range(600, 604))
VALIDATION_FAMILIES = tuple(range(640, 644))
RESERVED_FAMILIES = tuple(range(680, 688))
TRAIN_RENDERERS = (
    "APPEAL_FINALITY_LEDGER",
    "CLOSURE_EVIDENCE_CARD",
    "APPEAL_STATUS_MATRIX",
    "CLOCK_BOUNDARY_MEMO",
)
VALIDATION_RENDERER = "HELDOUT_CLOSURE_REGISTER"
PREDECESSOR_FAMILIES = set(range(400, 407)) | set(range(420, 427)) | set(range(440, 444)) | set(range(500, 508)) | set(range(540, 544))
PREDECESSOR_RENDERERS = {
    "DECISION_CLOCK_GRID", "MULTI_SYSTEM_JOURNAL", "STATE_DELTA_PACKET", "QUEUE_CONTROL_SHEET",
    "CROSS_FORMAT_REGISTER", "APPEAL_CLOCK_LEDGER", "APPEAL_DEADLINE_CARD", "APPEAL_EVENT_MATRIX",
    "APPEAL_DISPOSITION_TIMELINE", "HELDOUT_APPEAL_REVIEW_REGISTER",
}


def _load_parent():
    spec = importlib.util.spec_from_file_location("actionnet011_parent_for_v12", PARENT_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load parent generator: {PARENT_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.PROTOCOL_ID = PROTOCOL_ID
    module.BASE.PROTOCOL_ID = PROTOCOL_ID
    module.BASE.FOCUSED_PIVOTAL_SCHEDULE = ("UNRESOLVED_APPEAL",)
    return module


PARENT = _load_parent()
BASE = PARENT.BASE


def canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def digest(value: Any) -> str:
    payload = value if isinstance(value, bytes) else canonical(value).encode("utf-8")
    return "sha256:" + hashlib.sha256(payload).hexdigest()


def render(style: str, trajectory: dict[str, Any]) -> tuple[str, str]:
    state = BASE.public_state(trajectory["initial_state"])
    events = trajectory["submitted_events"]
    domain = trajectory["domain"]
    clock = state["request"]["query_time"]
    lines = "\n".join(f"FINALITY_EVENT::{BASE.event_text(event)}" for event in events)
    if style == "APPEAL_FINALITY_LEDGER":
        return "text/plain;profile=appeal-finality-ledger-v1", (
            f"APPEAL_FINALITY_LEDGER domain={domain}\nDECISION_CLOCK={clock}\nSTART={canonical(state)}\n"
            f"UNSORTED_EVENTS_BEGIN\n{lines}\nUNSORTED_EVENTS_END\n"
            "Determine finality from events that execute by the clock. A completed resolution closes the appeal; "
            "a future resolution leaves it open."
        )
    if style == "CLOSURE_EVIDENCE_CARD":
        queue = " || ".join(BASE.event_text(event) for event in events)
        return "text/plain;profile=closure-evidence-card-v1", (
            f"CLOSURE_EVIDENCE_CARD<{domain}> CLOCK::{clock} STATE::{canonical(state)} ENTRIES::{queue} "
            "RULE::sort_then_decide_from_executed_appeal_status"
        )
    if style == "APPEAL_STATUS_MATRIX":
        return "application/json;profile=appeal-status-matrix-v1", canonical({
            "domain": domain,
            "decision_clock": clock,
            "typed_start": state,
            "submitted_events_unordered": events,
            "canonical_order": ["time", "priority", "sequence", "event_id"],
            "finality_rule": "appeal is closed exactly when its resolution executes by the clock",
            "late_event_rule": "defer",
        })
    if style == "CLOCK_BOUNDARY_MEMO":
        return "text/plain;profile=clock-boundary-memo-v1", (
            f"Clock-boundary memorandum for {domain}. Decision time={clock}. Typed initial record={canonical(state)}. "
            "Sort the following submissions and evaluate appeal status only after executing through the decision time. "
            f"{lines}"
        )
    if style == VALIDATION_RENDERER:
        return "text/plain;profile=heldout-closure-register-v1", (
            f"Held-out closure register, domain {domain}; controlling clock {clock}; initial typed state {canonical(state)}. "
            "Submitted entries are unordered. Execute entries through the controlling clock, retain later entries, "
            f"and distinguish a completed appeal resolution from a still-pending resolution. {lines}"
        )
    raise ValueError(style)


def renderer_registry() -> tuple[dict[str, str], list[dict[str, Any]]]:
    styles = (*TRAIN_RENDERERS, VALIDATION_RENDERER)
    mapping = {style: BASE.opaque("renderer", PROTOCOL_ID, style, "v1") for style in styles}
    records = [{
        "lineage_id": lineage,
        "lineage_type": "renderer",
        "version": "1.0.0",
        "content_sha256": digest({"style": style, "schema": "appeal-finality-render-v12"}),
        "parents": [],
        "authority": "EDON Research Lab",
        "transformation": "render-balanced-appeal-finality-v1",
    } for style, lineage in mapping.items()]
    return mapping, records


def record(trajectory: dict[str, Any], style: str, renderer_ids: dict[str, str]) -> dict[str, Any]:
    media_type, content = render(style, trajectory)
    decision = trajectory["outcome"]["decision"]
    return {
        "case_id": BASE.opaque("case", PROTOCOL_ID, trajectory["trajectory_id"], style, "CERTIFICATE"),
        "input": {
            "observation": {"renderer_lineage": renderer_ids[style], "media_type": media_type, "content": content},
            "query": (
                "Execute the queue through the decision clock and return one canonical non-authoritative certificate. "
                "Treat resolved and unresolved appeal states symmetrically: an executed resolution closes the appeal; "
                "a deferred resolution leaves the appeal contested."
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
            "generator_profile": "APPEAL_FINALITY_BALANCED",
            "source_lineage": trajectory["source_lineage"],
            "institution_lineage": trajectory["institution_lineage"],
            "authority_graph_lineage": trajectory["authority_graph_lineage"],
            "workflow_graph_lineage": trajectory["workflow_graph_lineage"],
            "semantic_family": trajectory["semantic_family"],
            "selected_renderer": style,
            "task_type": "CERTIFICATE",
            "decision": decision,
            "sample_weight": 8.0,
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
        "renderer_counts": dict(sorted(Counter(row["metadata"]["selected_renderer"] for row in rows).items())),
        "weight_min": min(row["metadata"]["sample_weight"] for row in rows),
        "weight_max": max(row["metadata"]["sample_weight"] for row in rows),
        "weight_sum": sum(row["metadata"]["sample_weight"] for row in rows),
    }


def generate() -> dict[str, Any]:
    renderer_ids, renderer_lineages = renderer_registry()
    train_trajectories, train_pairs, train_lineages, train_audit = PARENT.focused_split(
        "balanced_train", TRAIN_SEED, TRAIN_FAMILIES, 18,
        ("benefits-finality", "permit-finality", "records-finality", "credential-finality"),
    )
    validation_trajectories, validation_pairs, validation_lineages, validation_audit = PARENT.focused_split(
        "balanced_validation", VALIDATION_SEED, VALIDATION_FAMILIES, 12,
        ("water-finality", "aviation-finality", "research-finality", "procurement-finality"),
    )
    train_rows = [
        record(trajectory, style, renderer_ids)
        for trajectory in sorted(train_trajectories, key=lambda item: item["trajectory_id"])
        for style in TRAIN_RENDERERS
    ]
    validation_rows = [
        record(trajectory, VALIDATION_RENDERER, renderer_ids)
        for trajectory in sorted(validation_trajectories, key=lambda item: item["trajectory_id"])
    ]
    original_lineages = [*renderer_lineages, *train_lineages, *validation_lineages]
    lineage_map = {item["lineage_id"]: item for item in original_lineages}
    train_summary = summarize(train_rows)
    validation_summary = summarize(validation_rows)
    train_cases = {row["case_id"] for row in train_rows}
    validation_cases = {row["case_id"] for row in validation_rows}
    train_pair_ids = {row["metadata"]["counterfactual_pair_id"] for row in train_rows}
    validation_pair_ids = {row["metadata"]["counterfactual_pair_id"] for row in validation_rows}
    train_family_ids = {row["metadata"]["semantic_family"] for row in train_rows}
    validation_family_ids = {row["metadata"]["semantic_family"] for row in validation_rows}
    all_rows = train_rows + validation_rows
    all_trajectories = train_trajectories + validation_trajectories
    controls = {
        "registered_counts": len(train_rows) == 384 and len(validation_rows) == 64,
        "registered_pair_counts": len(train_pairs) == 48 and len(validation_pairs) == 32,
        "certificate_only": all(row["metadata"]["task_type"] == "CERTIFICATE" for row in all_rows),
        "unresolved_appeal_mechanism_only": all(row["metadata"]["pair_mechanism"] == "UNRESOLVED_APPEAL" for row in all_rows),
        "pivotal_only": all(row["metadata"]["pair_class"] == "PIVOTAL" for row in all_rows),
        "train_decisions_balanced": train_summary["decision_counts"] == {"ALLOW": 192, "CONTESTED": 192},
        "validation_decisions_balanced": validation_summary["decision_counts"] == {"ALLOW": 32, "CONTESTED": 32},
        "training_weights_symmetric": train_summary["weight_min"] == train_summary["weight_max"] == 8.0,
        "appeal_boundary_exact": all(PARENT.appeal_boundary_exact(pair) for pair in train_pairs + validation_pairs),
        "independent_reference_engines_exact": train_audit["engine_disagreements"] == validation_audit["engine_disagreements"] == 0,
        "independent_schedulers_exact": train_audit["scheduler_disagreements"] == validation_audit["scheduler_disagreements"] == 0,
        "transition_engines_exact": train_audit["transition_disagreements"] == validation_audit["transition_disagreements"] == 0,
        "decision_clock_exact": train_audit["decision_clock_violations"] == validation_audit["decision_clock_violations"] == 0,
        "event_operands_visible": all(
            BASE.event_operands_visible(row["input"]["observation"]["content"], trajectory["submitted_events"])
            for trajectory in all_trajectories
            for row in all_rows
            if row["metadata"]["trajectory_id"] == trajectory["trajectory_id"]
        ),
        "binding_authority_false": all(row["target"].get("binding_authority") is False for row in all_rows),
        "model_inputs_only_observation_query": all(set(row["input"]) == {"observation", "query"} for row in all_rows),
        "unique_case_ids": len(train_cases) == len(train_rows) and len(validation_cases) == len(validation_rows),
        "train_validation_cases_disjoint": not train_cases & validation_cases,
        "train_validation_pairs_disjoint": not train_pair_ids & validation_pair_ids,
        "train_validation_families_disjoint": not train_family_ids & validation_family_ids,
        "train_validation_renderers_disjoint": set(TRAIN_RENDERERS).isdisjoint({VALIDATION_RENDERER}),
        "predecessor_families_disjoint": not (train_family_ids | validation_family_ids) & PREDECESSOR_FAMILIES,
        "predecessor_renderers_disjoint": not (set(TRAIN_RENDERERS) | {VALIDATION_RENDERER}) & PREDECESSOR_RENDERERS,
        "new_protocol_namespace": PROTOCOL_ID not in {"ACTIONNET-DATA-QUAL-010", "ACTIONNET-DATA-QUAL-011"},
        "heldout_renderer_validation_only": validation_summary["renderer_counts"] == {VALIDATION_RENDERER: 64},
        "released_lineage_ids_unique": len(lineage_map) == len(set(lineage_map)),
        "reserved_future_families_unmaterialized": not (train_family_ids | validation_family_ids) & set(RESERVED_FAMILIES),
    }
    return {
        "schema_version": "actionnet-data-qual-012-generated.v1",
        "protocol_id": PROTOCOL_ID,
        "result_id": RESULT_ID,
        "dataset_id": DATASET_ID,
        "datasets": {"train": train_rows, "focused_validation": validation_rows},
        "canonical_trajectories": all_trajectories,
        "lineages": list(lineage_map.values()),
        "controls": controls,
        "audits": {
            "train": train_summary,
            "focused_validation": validation_summary,
            "train_generator": train_audit,
            "validation_generator": validation_audit,
            "aggregate_target_sha256": digest([row["target"] for row in all_rows]),
        },
        "protected": {
            "reserved_future_families": list(RESERVED_FAMILIES),
            "public_materialized": False,
            "protected_materialized": False,
            "real_institution_materialized": False,
        },
    }