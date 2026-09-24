#!/usr/bin/env python3
"""Generate fresh queue-integrity and appeal-boundary repair data."""

from __future__ import annotations

import hashlib
import importlib.util
import json
from collections import Counter, defaultdict
from copy import deepcopy
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent
BASE_PATH = ROOT.parent / "ACTIONNET-DATA-QUAL-009" / "actionnet_multigen.py"
PROTOCOL_ID = "ACTIONNET-DATA-QUAL-010"
RESULT_ID = "ACTIONNET-DATA-QUAL-010-result-v1.0.0"
DATASET_ID = "ACTIONNET-QUEUE-INTEGRITY-APPEAL-REPAIR-v10.0.0"
TRAIN_PROFILES = {
    "CLOCK_GRID": ("DECISION_CLOCK_GRID", "MULTI_SYSTEM_JOURNAL"),
    "CONTROL_SHEET": ("STATE_DELTA_PACKET", "QUEUE_CONTROL_SHEET"),
}
VALIDATION_PROFILE = "REGISTER"
VALIDATION_RENDERER = "CROSS_FORMAT_REGISTER"
TRAIN_FAMILIES = {
    "CLOCK_GRID": tuple(range(400, 407)),
    "CONTROL_SHEET": tuple(range(420, 427)),
}
VALIDATION_FAMILIES = tuple(range(440, 444))
TRAIN_SEEDS = {"CLOCK_GRID": 26090410, "CONTROL_SHEET": 26090411}
VALIDATION_SEED = 26090412
SCORED_TASKS = ("CERTIFICATE", "TRANSITION", "QUEUE_TRACE", "PAIR_CONTRAST")
TRAIN_TASKS = (*SCORED_TASKS, "QUEUE_ORDER", "QUEUE_PARTITION")
RB1_TRAIN_FAMILIES = set(range(300, 324))
RB1_VALIDATION_FAMILIES = set(range(340, 346))
RB1_RENDERERS = {
    "CHRONOLOGY_LEDGER", "AUTHORIZATION_WORKPAD", "QUEUE_MATRIX",
    "STATE_TRANSITION_CARD", "DEPENDENCY_GRAPH_PACKET",
}


def _load_base():
    spec = importlib.util.spec_from_file_location("actionnet009_base_for_v10", BASE_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load predecessor generator: {BASE_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.PROTOCOL_ID = PROTOCOL_ID
    return module


BASE = _load_base()


def canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def digest(value: Any) -> str:
    data = value if isinstance(value, bytes) else canonical(value).encode("utf-8")
    return "sha256:" + hashlib.sha256(data).hexdigest()


def observation(style: str, renderer_ids: dict[str, str], trajectory: dict[str, Any]) -> dict[str, Any]:
    media_type, content = BASE.render(
        style, trajectory["domain"], trajectory["initial_state"], trajectory["submitted_events"]
    )
    return {"renderer_lineage": renderer_ids[style], "media_type": media_type, "content": content}


def metadata(trajectory: dict[str, Any], style: str, task_type: str, weight: float) -> dict[str, Any]:
    return {
        "trajectory_id": trajectory["trajectory_id"],
        "counterfactual_pair_id": trajectory["counterfactual_pair_id"],
        "pair_class": trajectory["pair_class"],
        "variant": trajectory["variant"],
        "intervention_family": trajectory["intervention_family"],
        "pair_mechanism": trajectory["pair_mechanism"],
        "generator_lineage": trajectory["generator_lineage"],
        "generator_profile": trajectory["generator_profile"],
        "source_lineage": trajectory["source_lineage"],
        "institution_lineage": trajectory["institution_lineage"],
        "authority_graph_lineage": trajectory["authority_graph_lineage"],
        "workflow_graph_lineage": trajectory["workflow_graph_lineage"],
        "semantic_family": trajectory["semantic_family"],
        "selected_renderer": style,
        "task_type": task_type,
        "decision": trajectory["outcome"]["decision"],
        "sample_weight": round(weight, 6),
        "training_fields": ["input", "target"],
    }


def task_weight(trajectory: dict[str, Any], task_type: str) -> float:
    base = {
        "CERTIFICATE": 4.0,
        "TRANSITION": 4.0,
        "QUEUE_TRACE": 8.0,
        "QUEUE_ORDER": 6.0,
        "QUEUE_PARTITION": 8.0,
    }[task_type]
    if trajectory["pair_class"] == "PIVOTAL":
        base *= 1.5
    if trajectory["pair_mechanism"] == "UNRESOLVED_APPEAL":
        base *= 2.0
    if task_type == "CERTIFICATE" and trajectory["outcome"]["decision"] != "ALLOW":
        base *= 1.25
    return base


def state_record(
    trajectory: dict[str, Any], style: str, renderer_ids: dict[str, str], task_type: str
) -> dict[str, Any]:
    receipt = trajectory["execution_receipt"]
    public_state = BASE.public_state(trajectory["final_state"])
    targets = {
        "CERTIFICATE": deepcopy(trajectory["outcome"]),
        "TRANSITION": {
            "post_state": public_state,
            "semantic_state": trajectory["outcome"]["semantic_state"],
            "decision": trajectory["outcome"]["decision"],
            "failed_conditions": trajectory["outcome"]["failed_conditions"],
            "binding_authority": False,
        },
        "QUEUE_TRACE": {
            "ordered_event_ids": receipt["ordered_event_ids"],
            "executed_event_ids": receipt["executed_event_ids"],
            "deferred_event_ids": receipt["deferred_event_ids"],
            "step_semantics": BASE.compact_step_semantics(receipt),
            "final_state": public_state,
            "binding_authority": False,
        },
        "QUEUE_ORDER": {
            "ordered_event_ids": receipt["ordered_event_ids"],
            "binding_authority": False,
        },
        "QUEUE_PARTITION": {
            "ordered_event_ids": receipt["ordered_event_ids"],
            "executed_event_ids": receipt["executed_event_ids"],
            "deferred_event_ids": receipt["deferred_event_ids"],
            "binding_authority": False,
        },
    }
    queries = {
        "CERTIFICATE": "Apply the deterministic event queue through the disposition time and return one canonical non-authoritative institutional certificate.",
        "TRANSITION": "Apply the queue and return exactly: post_state, semantic_state, decision, failed_conditions, and binding_authority=false. Digests and changed fields are derived deterministically after generation.",
        "QUEUE_TRACE": "Return exactly: ordered_event_ids, executed_event_ids, deferred_event_ids, compact step_semantics, final_state, and binding_authority=false. Do not calculate hashes.",
        "QUEUE_ORDER": "Return exactly ordered_event_ids and binding_authority=false. Include every submitted event identifier exactly once in ascending time, priority, sequence, and event-identifier order.",
        "QUEUE_PARTITION": "Return exactly ordered_event_ids, executed_event_ids, deferred_event_ids, and binding_authority=false. The latter two lists must be disjoint exhaustive order-preserving subsequences of ordered_event_ids split by time<=decision_clock.",
    }
    return {
        "case_id": BASE.opaque("case", PROTOCOL_ID, trajectory["trajectory_id"], style, task_type),
        "input": {"observation": observation(style, renderer_ids, trajectory), "query": queries[task_type]},
        "target": targets[task_type],
        "metadata": metadata(trajectory, style, task_type, task_weight(trajectory, task_type)),
    }


def pair_record(pair: dict[str, Any], style: str, renderer_ids: dict[str, str]) -> dict[str, Any]:
    base = pair["base"]
    comparison = pair["comparison"]
    base_obs = observation(style, renderer_ids, base)
    comparison_obs = observation(style, renderer_ids, comparison)
    weight = 6.0 if pair["pair_class"] == "PIVOTAL" else 3.0
    if pair["intervention_family"] == "UNRESOLVED_APPEAL":
        weight *= 2.0
    row = {
        "case_id": BASE.opaque("case", PROTOCOL_ID, pair["counterfactual_pair_id"], style, "PAIR_CONTRAST"),
        "input": {
            "observation": {
                "renderer_lineage": renderer_ids[style],
                "media_type": "application/json;profile=event-queue-pair-v1",
                "content": canonical({
                    "base_observation": base_obs["content"],
                    "comparison_observation": comparison_obs["content"],
                }),
            },
            "query": "Execute both queues and return exactly decision_changed, both certificates, causal_event_change_paths, changed_post_state_paths, and binding_authority=false.",
        },
        "target": {
            "decision_changed": base["outcome"]["decision"] != comparison["outcome"]["decision"],
            "base_certificate": base["outcome"],
            "comparison_certificate": comparison["outcome"],
            "causal_event_change_paths": sorted(BASE.changed_fields(base["submitted_events"], comparison["submitted_events"])),
            "changed_post_state_paths": sorted(BASE.changed_fields(base["final_state"], comparison["final_state"])),
            "binding_authority": False,
        },
        "metadata": {
            **metadata(base, style, "PAIR_CONTRAST", weight),
            "trajectory_id": None,
            "variant": "PAIR",
            "intervention_family": pair["intervention_family"],
            "decision": comparison["outcome"]["decision"],
        },
    }
    return row


def renderer_registry() -> tuple[dict[str, str], list[dict[str, Any]]]:
    styles = tuple(style for values in TRAIN_PROFILES.values() for style in values) + (VALIDATION_RENDERER,)
    mapping = {style: BASE.opaque("renderer", PROTOCOL_ID, style, "v1") for style in styles}
    records = [
        {
            "lineage_id": lineage,
            "lineage_type": "renderer",
            "version": "1.0.0",
            "content_sha256": digest({"style": style, "schema": "actionnet-event-render-v10"}),
            "parents": [],
            "authority": "EDON Research Lab",
            "transformation": "render-eventnet-v10",
        }
        for style, lineage in mapping.items()
    ]
    return mapping, records


def mechanism_balanced_state_pairs(pairs: list[dict[str, Any]]) -> set[str]:
    selected: set[str] = set()
    targets = {"PIVOTAL": 16, "INVARIANCE": 4, "CONTEXTUAL": 4}
    for pair_class, count in targets.items():
        buckets: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for pair in pairs:
            if pair["pair_class"] == pair_class:
                buckets[pair["intervention_family"]].append(pair)
        for values in buckets.values():
            values.sort(key=lambda item: item["counterfactual_pair_id"])
        while sum(pair_id in selected for pair_id in [p["counterfactual_pair_id"] for p in pairs if p["pair_class"] == pair_class]) < count:
            progressed = False
            for mechanism in sorted(buckets):
                if buckets[mechanism] and sum(
                    p["counterfactual_pair_id"] in selected for p in pairs if p["pair_class"] == pair_class
                ) < count:
                    selected.add(buckets[mechanism].pop(0)["counterfactual_pair_id"])
                    progressed = True
            if not progressed:
                raise ValueError(f"cannot select {count} validation state pairs for {pair_class}")
    return selected


def is_subsequence(values: list[str], ordered: list[str]) -> bool:
    cursor = iter(ordered)
    return all(any(candidate == value for candidate in cursor) for value in values)


def queue_integrity(trajectory: dict[str, Any]) -> bool:
    receipt = trajectory["execution_receipt"]
    ordered = receipt["ordered_event_ids"]
    executed = receipt["executed_event_ids"]
    deferred = receipt["deferred_event_ids"]
    submitted = [event["event_id"] for event in trajectory["submitted_events"]]
    return (
        len(ordered) == len(set(ordered)) == len(submitted)
        and set(ordered) == set(submitted)
        and not (set(executed) & set(deferred))
        and set(executed) | set(deferred) == set(ordered)
        and is_subsequence(executed, ordered)
        and is_subsequence(deferred, ordered)
    )


def summarize_records(rows: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "records": len(rows),
        "case_ids": len({row["case_id"] for row in rows}),
        "task_counts": dict(sorted(Counter(row["metadata"]["task_type"] for row in rows).items())),
        "profile_counts": dict(sorted(Counter(row["metadata"]["generator_profile"] for row in rows).items())),
        "renderer_counts": dict(sorted(Counter(row["metadata"]["selected_renderer"] for row in rows).items())),
        "weight_min": min(float(row["metadata"]["sample_weight"]) for row in rows),
        "weight_max": max(float(row["metadata"]["sample_weight"]) for row in rows),
        "weight_sum": round(sum(float(row["metadata"]["sample_weight"]) for row in rows), 6),
    }


def generate() -> dict[str, Any]:
    renderer_ids, renderer_lineages = renderer_registry()
    train_trajectories: list[dict[str, Any]] = []
    train_pairs: list[dict[str, Any]] = []
    lineages = list(renderer_lineages)
    split_audits: dict[str, Any] = {}
    domains = {
        "CLOCK_GRID": ("licensing-clock", "benefits-review", "supply-authorization", "records-release"),
        "CONTROL_SHEET": ("appeal-control", "credential-routing", "capacity-review", "jurisdiction-audit"),
    }
    for profile in ("CLOCK_GRID", "CONTROL_SHEET"):
        trajectories, pairs, profile_lineages, audit = BASE.generate_split(
            "train",
            TRAIN_SEEDS[profile],
            TRAIN_FAMILIES[profile],
            24,
            domains[profile],
            profile,
        )
        train_trajectories.extend(trajectories)
        train_pairs.extend(pairs)
        lineages.extend(profile_lineages)
        split_audits[profile] = audit
    validation_trajectories, validation_pairs, validation_lineages, validation_audit = BASE.generate_split(
        "repair_validation",
        VALIDATION_SEED,
        VALIDATION_FAMILIES,
        12,
        ("water-allocation-review", "identity-appeal-board", "aviation-records", "research-consortium"),
        VALIDATION_PROFILE,
    )
    lineages.extend(validation_lineages)

    train_rows: list[dict[str, Any]] = []
    trajectories_by_pair: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for trajectory in train_trajectories:
        trajectories_by_pair[trajectory["counterfactual_pair_id"]].append(trajectory)
    for index, pair in enumerate(sorted(train_pairs, key=lambda item: item["counterfactual_pair_id"])):
        profile = pair["base"]["generator_profile"]
        styles = TRAIN_PROFILES[profile]
        state_style = styles[index % len(styles)]
        for trajectory in sorted(trajectories_by_pair[pair["counterfactual_pair_id"]], key=lambda item: item["variant"]):
            for task in ("CERTIFICATE", "TRANSITION", "QUEUE_TRACE", "QUEUE_ORDER", "QUEUE_PARTITION"):
                train_rows.append(state_record(trajectory, state_style, renderer_ids, task))
        for style in styles:
            train_rows.append(pair_record(pair, style, renderer_ids))

    state_pair_ids = mechanism_balanced_state_pairs(validation_pairs)
    validation_rows: list[dict[str, Any]] = []
    validation_by_pair: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for trajectory in validation_trajectories:
        validation_by_pair[trajectory["counterfactual_pair_id"]].append(trajectory)
    for pair in sorted(validation_pairs, key=lambda item: item["counterfactual_pair_id"]):
        if pair["counterfactual_pair_id"] in state_pair_ids:
            for trajectory in sorted(validation_by_pair[pair["counterfactual_pair_id"]], key=lambda item: item["variant"]):
                for task in ("CERTIFICATE", "TRANSITION", "QUEUE_TRACE"):
                    validation_rows.append(state_record(trajectory, VALIDATION_RENDERER, renderer_ids, task))
        validation_rows.append(pair_record(pair, VALIDATION_RENDERER, renderer_ids))

    all_trajectories = train_trajectories + validation_trajectories
    train_cases = {row["case_id"] for row in train_rows}
    validation_cases = {row["case_id"] for row in validation_rows}
    train_pair_ids = {pair["counterfactual_pair_id"] for pair in train_pairs}
    validation_pair_ids = {pair["counterfactual_pair_id"] for pair in validation_pairs}
    train_families = {row["metadata"]["semantic_family"] for row in train_rows}
    validation_families = {row["metadata"]["semantic_family"] for row in validation_rows}
    train_renderers = {row["metadata"]["selected_renderer"] for row in train_rows}
    validation_renderers = {row["metadata"]["selected_renderer"] for row in validation_rows}
    validation_appeals = [
        row for row in validation_rows
        if row["metadata"]["task_type"] == "CERTIFICATE" and row["metadata"]["pair_mechanism"] == "UNRESOLVED_APPEAL"
    ]
    train_summary = summarize_records(train_rows)
    validation_summary = summarize_records(validation_rows)
    controls = {
        "registered_counts": len(train_rows) == 4032 and len(validation_rows) == 192,
        "unique_case_ids": len(train_cases) == len(train_rows) and len(validation_cases) == len(validation_rows),
        "train_task_balance": train_summary["task_counts"] == {task: 672 for task in sorted(TRAIN_TASKS)},
        "validation_task_balance": validation_summary["task_counts"] == {task: 48 for task in sorted(SCORED_TASKS)},
        "train_pair_count": len(train_pair_ids) == 336,
        "validation_pair_count": len(validation_pair_ids) == 48,
        "queue_integrity_exact": all(queue_integrity(trajectory) for trajectory in all_trajectories),
        "independent_reference_engines_exact": all(audit["engine_disagreements"] == 0 for audit in [*split_audits.values(), validation_audit]),
        "independent_schedulers_exact": all(audit["scheduler_disagreements"] == 0 for audit in [*split_audits.values(), validation_audit]),
        "transitions_exact": all(audit["transition_disagreements"] == 0 for audit in [*split_audits.values(), validation_audit]),
        "pivotal_pairs_change": all(audit["pivotal_pair_changes"] == audit["pair_class_distribution"]["PIVOTAL"] for audit in [*split_audits.values(), validation_audit]),
        "invariance_pairs_preserve": all(audit["invariance_pair_changes"] == 0 for audit in [*split_audits.values(), validation_audit]),
        "contextual_pairs_preserve": all(audit["contextual_pair_changes"] == 0 for audit in [*split_audits.values(), validation_audit]),
        "decision_clock_exact": all(audit["decision_clock_violations"] == 0 for audit in [*split_audits.values(), validation_audit]),
        "deferral_on_every_trajectory": all(audit["deferred_event_trajectories"] > 0 for audit in [*split_audits.values(), validation_audit]),
        "all_pivotal_mechanisms_in_training": all(set(BASE.PIVOTAL_MECHANISMS).issubset(audit["mechanism_distribution"]) for audit in split_audits.values()),
        "all_pivotal_mechanisms_in_validation": set(BASE.PIVOTAL_MECHANISMS).issubset(validation_audit["mechanism_distribution"]),
        "all_pivotal_mechanisms_in_scored_certificate_subset": set(BASE.PIVOTAL_MECHANISMS).issubset({row["metadata"]["pair_mechanism"] for row in validation_rows if row["metadata"]["task_type"] == "CERTIFICATE"}),
        "unresolved_appeal_scored_both_sides": {row["target"]["decision"] for row in validation_appeals} == {"ALLOW", "CONTESTED"},
        "queue_auxiliary_supervision_present": train_summary["task_counts"].get("QUEUE_ORDER") == 672 and train_summary["task_counts"].get("QUEUE_PARTITION") == 672,
        "train_validation_cases_disjoint": not (train_cases & validation_cases),
        "train_validation_pairs_disjoint": not (train_pair_ids & validation_pair_ids),
        "train_validation_families_disjoint": not (train_families & validation_families),
        "train_validation_renderers_disjoint": not (train_renderers & validation_renderers),
        "rb1_semantic_families_disjoint": not ((train_families | validation_families) & (RB1_TRAIN_FAMILIES | RB1_VALIDATION_FAMILIES)),
        "rb1_renderers_disjoint": not ((train_renderers | validation_renderers) & RB1_RENDERERS),
        "new_protocol_namespace": PROTOCOL_ID != "ACTIONNET-DATA-QUAL-009",
        "binding_authority_false": all(row["target"].get("binding_authority") is False for row in train_rows + validation_rows),
        "model_inputs_only_observation_query": all(set(row["input"]) == {"observation", "query"} for row in train_rows + validation_rows),
        "heldout_renderer_only_in_validation": validation_renderers == {VALIDATION_RENDERER},
        "two_training_profiles_balanced": train_summary["profile_counts"] == {"CLOCK_GRID": 2016, "CONTROL_SHEET": 2016},
        "no_duplicate_lineage_ids": len({row["lineage_id"] for row in lineages}) == len(lineages),
    }
    return {
        "schema_version": "actionnet-data-qual-010-generated.v1",
        "protocol_id": PROTOCOL_ID,
        "result_id": RESULT_ID,
        "dataset_id": DATASET_ID,
        "datasets": {"train": train_rows, "repair_validation": validation_rows},
        "canonical_trajectories": all_trajectories,
        "lineages": lineages,
        "audits": {
            "train": train_summary,
            "repair_validation": validation_summary,
            "train_profiles": split_audits,
            "repair_validation_profile": validation_audit,
            "validation_state_pair_count": len(state_pair_ids),
            "validation_unresolved_appeal_certificates": len(validation_appeals),
            "train_semantic_families": sorted(train_families),
            "validation_semantic_families": sorted(validation_families),
            "train_renderers": sorted(train_renderers),
            "validation_renderers": sorted(validation_renderers),
            "aggregate_target_sha256": digest([row["target"] for row in train_rows + validation_rows]),
        },
        "controls": controls,
        "protected": {
            "future_transfer_families": list(range(460, 466)),
            "protected_families": list(range(470, 476)),
            "public_materialized": False,
            "protected_materialized": False,
            "real_institution_materialized": False,
        },
    }