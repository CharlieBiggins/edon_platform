#!/usr/bin/env python3
"""Generate the fresh 192-case DEV-014 full-regression instrument."""

from __future__ import annotations

import hashlib
import importlib.util
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent
PARENT_PATH = ROOT.parent / "ACTIONNET-DATA-QUAL-010" / "actionnet010.py"
PROTOCOL_ID = "ACTIONNET-DATA-QUAL-014"
RESULT_ID = "ACTIONNET-DATA-QUAL-014-result-v1.0.0"
DATASET_ID = "ACTIONNET-FRESH-FULL-MULTITASK-REGRESSION-v14.0.0"
VALIDATION_SEED = 26090580
VALIDATION_FAMILIES = tuple(range(780, 784))
RESERVED_FAMILIES = tuple(range(784, 788))
VALIDATION_PROFILE = "FULL_REGRESSION"
VALIDATION_RENDERER = "HELDOUT_FULL_REGRESSION_REGISTER"
SCORED_TASKS = ("CERTIFICATE", "TRANSITION", "QUEUE_TRACE", "PAIR_CONTRAST")
PREDECESSOR_FAMILIES = set(range(300, 748))
PREDECESSOR_RENDERERS = {
    "CHRONOLOGY_LEDGER", "AUTHORIZATION_WORKPAD", "QUEUE_MATRIX", "STATE_TRANSITION_CARD",
    "DEPENDENCY_GRAPH_PACKET", "DECISION_CLOCK_GRID", "MULTI_SYSTEM_JOURNAL", "STATE_DELTA_PACKET",
    "QUEUE_CONTROL_SHEET", "CROSS_FORMAT_REGISTER", "APPEAL_CLOCK_LEDGER", "APPEAL_DEADLINE_CARD",
    "APPEAL_EVENT_MATRIX", "APPEAL_DISPOSITION_TIMELINE", "HELDOUT_APPEAL_REVIEW_REGISTER",
    "APPEAL_FINALITY_LEDGER", "CLOSURE_EVIDENCE_CARD", "APPEAL_STATUS_MATRIX", "CLOCK_BOUNDARY_MEMO",
    "HELDOUT_CLOSURE_REGISTER", "BOUNDARY_DELTA_LEDGER", "EXECUTION_CUTOFF_CARD",
    "APPEAL_PAIR_MATRIX", "NEAR_CLOCK_MEMO", "HELDOUT_BOUNDARY_SELECTION_REGISTER",
    "HELDOUT_BOUNDARY_CONFIRMATION_DOCKET",
}


def _load_parent():
    spec = importlib.util.spec_from_file_location("actionnet010_parent_for_v14", PARENT_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load predecessor generator: {PARENT_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.PROTOCOL_ID = PROTOCOL_ID
    module.BASE.PROTOCOL_ID = PROTOCOL_ID
    return module


PARENT = _load_parent()
BASE = PARENT.BASE


def canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def digest(value: Any) -> str:
    payload = value if isinstance(value, bytes) else canonical(value).encode("utf-8")
    return "sha256:" + hashlib.sha256(payload).hexdigest()


def observation(style: str, renderer_ids: dict[str, str], trajectory: dict[str, Any]) -> dict[str, Any]:
    if style != VALIDATION_RENDERER:
        raise ValueError(style)
    state = BASE.public_state(trajectory["initial_state"])
    content = canonical({
        "domain": trajectory["domain"],
        "decision_clock": state["request"]["query_time"],
        "initial_state": state,
        "submitted_events_unordered": trajectory["submitted_events"],
        "ordering_rule": ["time", "priority", "sequence", "event_id"],
        "execution_rule": "event.time <= decision_clock",
        "late_event_rule": "defer",
    })
    return {
        "renderer_lineage": renderer_ids[style],
        "media_type": "application/json;profile=heldout-full-regression-register-v1",
        "content": content,
    }


PARENT.observation = observation


def renderer_registry() -> tuple[dict[str, str], list[dict[str, Any]]]:
    lineage = BASE.opaque("renderer", PROTOCOL_ID, VALIDATION_RENDERER, "v1")
    return {VALIDATION_RENDERER: lineage}, [{
        "lineage_id": lineage,
        "lineage_type": "renderer",
        "version": "1.0.0",
        "content_sha256": digest({"style": VALIDATION_RENDERER, "schema": "full-regression-render-v14"}),
        "parents": [],
        "authority": "EDON Research Lab",
        "transformation": "render-heldout-full-regression-v1",
    }]


def summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "records": len(rows),
        "case_ids": len({row["case_id"] for row in rows}),
        "pair_ids": len({row["metadata"]["counterfactual_pair_id"] for row in rows}),
        "task_counts": dict(sorted(Counter(row["metadata"]["task_type"] for row in rows).items())),
        "profile_counts": dict(sorted(Counter(row["metadata"]["generator_profile"] for row in rows).items())),
        "renderer_counts": dict(sorted(Counter(row["metadata"]["selected_renderer"] for row in rows).items())),
        "pair_class_counts": dict(sorted(Counter(row["metadata"]["pair_class"] for row in rows).items())),
    }


def generate() -> dict[str, Any]:
    renderer_ids, renderer_lineages = renderer_registry()
    trajectories, pairs, lineages, generator_audit = BASE.generate_split(
        "full_regression",
        VALIDATION_SEED,
        VALIDATION_FAMILIES,
        12,
        ("public-health-review", "infrastructure-allocation", "education-licensing", "research-oversight"),
        VALIDATION_PROFILE,
    )
    for lineage in lineages:
        if lineage["lineage_type"] == "generator":
            lineage["content_sha256"] = digest({
                "protocol": PROTOCOL_ID,
                "seed": VALIDATION_SEED,
                "families": VALIDATION_FAMILIES,
                "implementation": "fresh-full-multitask-regression-v1",
            })
            lineage["parents"] = ["ACTIONNET-DATA-QUAL-010-result-v1.0.0"]
            lineage["transformation"] = "generate-fresh-full-regression-v1"
    state_pair_ids = PARENT.mechanism_balanced_state_pairs(pairs)
    by_pair: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for trajectory in trajectories:
        by_pair[trajectory["counterfactual_pair_id"]].append(trajectory)
    rows: list[dict[str, Any]] = []
    for pair in sorted(pairs, key=lambda item: item["counterfactual_pair_id"]):
        pair_id = pair["counterfactual_pair_id"]
        if pair_id in state_pair_ids:
            for trajectory in sorted(by_pair[pair_id], key=lambda item: item["variant"]):
                for task in ("CERTIFICATE", "TRANSITION", "QUEUE_TRACE"):
                    rows.append(PARENT.state_record(trajectory, VALIDATION_RENDERER, renderer_ids, task))
        rows.append(PARENT.pair_record(pair, VALIDATION_RENDERER, renderer_ids))
    summary = summarize(rows)
    family_ids = {row["metadata"]["semantic_family"] for row in rows}
    appeal_certificates = [
        row for row in rows
        if row["metadata"]["task_type"] == "CERTIFICATE"
        and row["metadata"]["pair_mechanism"] == "UNRESOLVED_APPEAL"
    ]
    lineage_rows = [*renderer_lineages, *lineages]
    controls = {
        "registered_count_192": len(rows) == 192,
        "unique_case_ids": summary["case_ids"] == 192,
        "registered_pair_count_48": len(pairs) == summary["pair_ids"] == 48,
        "task_balance_48_each": summary["task_counts"] == {task: 48 for task in sorted(SCORED_TASKS)},
        "state_pair_count_24": len(state_pair_ids) == 24,
        "heldout_profile_only": summary["profile_counts"] == {VALIDATION_PROFILE: 192},
        "heldout_renderer_only": summary["renderer_counts"] == {VALIDATION_RENDERER: 192},
        "all_pair_classes_scored": set(summary["pair_class_counts"]) == {"CONTEXTUAL", "INVARIANCE", "PIVOTAL"},
        "all_pivotal_mechanisms_present": set(BASE.PIVOTAL_MECHANISMS).issubset(generator_audit["mechanism_distribution"]),
        "all_pivotal_mechanisms_in_certificates": set(BASE.PIVOTAL_MECHANISMS).issubset({row["metadata"]["pair_mechanism"] for row in rows if row["metadata"]["task_type"] == "CERTIFICATE"}),
        "unresolved_appeal_scored_both_sides": {row["target"]["decision"] for row in appeal_certificates} == {"ALLOW", "CONTESTED"},
        "queue_integrity_exact": all(PARENT.queue_integrity(trajectory) for trajectory in trajectories),
        "independent_reference_engines_exact": generator_audit["engine_disagreements"] == 0,
        "independent_schedulers_exact": generator_audit["scheduler_disagreements"] == 0,
        "transition_engines_exact": generator_audit["transition_disagreements"] == 0,
        "pivotal_pairs_change": generator_audit["pivotal_pair_changes"] == generator_audit["pair_class_distribution"]["PIVOTAL"],
        "invariance_pairs_preserve": generator_audit["invariance_pair_changes"] == 0,
        "contextual_pairs_preserve": generator_audit["contextual_pair_changes"] == 0,
        "decision_clock_exact": generator_audit["decision_clock_violations"] == 0,
        "deferral_present": generator_audit["deferred_event_trajectories"] > 0,
        "predecessor_families_disjoint": not family_ids & PREDECESSOR_FAMILIES,
        "predecessor_renderers_disjoint": VALIDATION_RENDERER not in PREDECESSOR_RENDERERS,
        "reserved_future_families_unmaterialized": not family_ids & set(RESERVED_FAMILIES),
        "binding_authority_false": all(row["target"].get("binding_authority") is False for row in rows),
        "model_inputs_only_observation_query": all(set(row["input"]) == {"observation", "query"} for row in rows),
        "event_operands_visible": all(BASE.event_operands_visible(observation(VALIDATION_RENDERER, renderer_ids, trajectory)["content"], trajectory["submitted_events"]) for trajectory in trajectories),
        "lineage_ids_unique": len({row["lineage_id"] for row in lineage_rows}) == len(lineage_rows),
        "new_protocol_namespace": PROTOCOL_ID == "ACTIONNET-DATA-QUAL-014",
        "fresh_seed_registered": VALIDATION_SEED == 26090580,
        "no_training_split": True,
    }
    return {
        "schema_version": "actionnet-data-qual-014-generated.v1",
        "protocol_id": PROTOCOL_ID,
        "result_id": RESULT_ID,
        "dataset_id": DATASET_ID,
        "datasets": {"full_regression": rows},
        "canonical_trajectories": trajectories,
        "lineages": lineage_rows,
        "controls": controls,
        "audits": {
            "full_regression": summary,
            "generator": generator_audit,
            "state_pair_count": len(state_pair_ids),
            "unresolved_appeal_certificates": len(appeal_certificates),
            "semantic_families": sorted(family_ids),
            "aggregate_target_sha256": digest([row["target"] for row in rows]),
        },
        "protected": {
            "reserved_future_families": list(RESERVED_FAMILIES),
            "single_candidate_full_regression": True,
            "public_materialized": False,
            "protected_materialized": False,
            "real_institution_materialized": False,
        },
    }