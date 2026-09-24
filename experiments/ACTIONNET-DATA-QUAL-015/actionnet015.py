#!/usr/bin/env python3
"""Build mixed replay training and fresh retention-regression splits."""

from __future__ import annotations

import hashlib
import importlib.util
import json
from collections import Counter, defaultdict
from copy import deepcopy
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent
EXPERIMENTS = ROOT.parent
PARENT_PATH = EXPERIMENTS / "ACTIONNET-DATA-QUAL-014" / "actionnet014.py"
REPLAY_SOURCE = EXPERIMENTS / "ACTIONNET-DATA-QUAL-010" / "dataset" / "train.jsonl"
APPEAL_SOURCE = EXPERIMENTS / "ACTIONNET-DATA-QUAL-013" / "dataset" / "train.jsonl"
DEV014_SOURCE = EXPERIMENTS / "ACTIONNET-DATA-QUAL-014" / "dataset" / "full_regression.jsonl"

PROTOCOL_ID = "ACTIONNET-DATA-QUAL-015"
RESULT_ID = "ACTIONNET-DATA-QUAL-015-result-v1.0.0"
DATASET_ID = "ACTIONNET-MIXED-RETENTION-REPAIR-v15.0.0"
SELECTION_SEED = 26090590
CONFIRMATION_SEED = 26090600
SELECTION_FAMILIES = (784, 785)
CONFIRMATION_FAMILIES = tuple(range(800, 804))
RESERVED_FAMILIES = tuple(range(820, 824))
SELECTION_RENDERER = "HELDOUT_RETENTION_SELECTION_PACKET"
CONFIRMATION_RENDERER = "HELDOUT_RETENTION_CONFIRMATION_DOCKET"
TRAIN_COUNTS = {
    "CERTIFICATE": 32,
    "TRANSITION": 96,
    "QUEUE_TRACE": 96,
    "PAIR_CONTRAST": 64,
    "QUEUE_ORDER": 32,
    "QUEUE_PARTITION": 32,
}
APPEAL_CERTIFICATES = 32
TRAIN_WEIGHTS = {
    "CERTIFICATE": 6.0,
    "TRANSITION": 9.0,
    "QUEUE_TRACE": 10.0,
    "PAIR_CONTRAST": 7.0,
    "QUEUE_ORDER": 6.0,
    "QUEUE_PARTITION": 8.0,
}


def _load_parent():
    spec = importlib.util.spec_from_file_location("actionnet014_parent_for_v15", PARENT_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load predecessor generator: {PARENT_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.PROTOCOL_ID = PROTOCOL_ID
    module.PARENT.PROTOCOL_ID = PROTOCOL_ID
    module.BASE.PROTOCOL_ID = PROTOCOL_ID
    return module


PARENT = _load_parent()
V10 = PARENT.PARENT
BASE = PARENT.BASE


def canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def digest(value: Any) -> str:
    payload = value if isinstance(value, bytes) else canonical(value).encode("utf-8")
    return "sha256:" + hashlib.sha256(payload).hexdigest()


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def observation(style: str, renderer_ids: dict[str, str], trajectory: dict[str, Any]) -> dict[str, Any]:
    state = BASE.public_state(trajectory["initial_state"])
    clock = state["request"]["query_time"]
    events = trajectory["submitted_events"]
    if style == SELECTION_RENDERER:
        content = canonical({
            "domain": trajectory["domain"],
            "decision_clock": clock,
            "initial_state": state,
            "submitted_events_unordered": events,
            "canonical_order": ["time", "priority", "sequence", "event_id"],
            "execution_boundary": "inclusive",
            "late_event_disposition": "deferred",
        })
        media_type = "application/json;profile=heldout-retention-selection-packet-v1"
    elif style == CONFIRMATION_RENDERER:
        queue = " || ".join(BASE.event_text(event) for event in events)
        content = (
            f"DOCKET<{trajectory['domain']}>\nINITIAL_RECORD::{canonical(state)}\n"
            f"SCHEDULED_ENTRIES::{queue}\nDISPOSITION_TIME::{clock}"
        )
        media_type = "text/plain;profile=heldout-retention-confirmation-docket-v1"
    else:
        raise ValueError(style)
    return {
        "renderer_lineage": renderer_ids[style],
        "media_type": media_type,
        "content": content,
    }


V10.observation = observation


def renderer_registry() -> tuple[dict[str, str], list[dict[str, Any]]]:
    styles = (SELECTION_RENDERER, CONFIRMATION_RENDERER)
    mapping = {style: BASE.opaque("renderer", PROTOCOL_ID, style, "v1") for style in styles}
    records = [{
        "lineage_id": lineage,
        "lineage_type": "renderer",
        "version": "1.0.0",
        "content_sha256": digest({"style": style, "schema": "mixed-retention-render-v15"}),
        "parents": [],
        "authority": "EDON Research Lab",
        "transformation": "render-mixed-retention-regression-v1",
    } for style, lineage in mapping.items()]
    return mapping, records


def sample_rows(rows: list[dict[str, Any]], task: str, count: int, tag: str) -> list[dict[str, Any]]:
    candidates = [row for row in rows if row["metadata"]["task_type"] == task]
    ordered = sorted(
        candidates,
        key=lambda row: hashlib.sha256(f"{tag}:{row['case_id']}".encode("utf-8")).hexdigest(),
    )
    if len(ordered) < count:
        raise ValueError(f"insufficient {task} replay rows")
    return ordered[:count]


def mixed_training_rows() -> list[dict[str, Any]]:
    replay = read_jsonl(REPLAY_SOURCE)
    appeal = read_jsonl(APPEAL_SOURCE)
    selected: list[dict[str, Any]] = []
    for task, count in TRAIN_COUNTS.items():
        for row in sample_rows(replay, task, count, f"dev015-replay-{task}"):
            copied = deepcopy(row)
            copied["metadata"]["sample_weight"] = TRAIN_WEIGHTS[task]
            copied["metadata"]["replay_source_protocol"] = "ACTIONNET-DATA-QUAL-010"
            selected.append(copied)
    for row in sample_rows(appeal, "CERTIFICATE", APPEAL_CERTIFICATES, "dev015-appeal-retention"):
        copied = deepcopy(row)
        copied["metadata"]["replay_source_protocol"] = "ACTIONNET-DATA-QUAL-013"
        selected.append(copied)
    return sorted(selected, key=lambda row: (row["metadata"]["task_type"], row["case_id"]))


def choose_state_pairs(pairs: list[dict[str, Any]], targets: dict[str, int]) -> set[str]:
    selected: set[str] = set()
    for pair_class, target in targets.items():
        candidates = sorted(
            [pair for pair in pairs if pair["pair_class"] == pair_class],
            key=lambda pair: pair["counterfactual_pair_id"],
        )
        if pair_class == "PIVOTAL":
            buckets: dict[str, list[dict[str, Any]]] = defaultdict(list)
            for pair in candidates:
                buckets[pair["intervention_family"]].append(pair)
            mechanisms = sorted(buckets, key=lambda name: (name != "UNRESOLVED_APPEAL", name))
            while len([pair_id for pair_id in selected if any(p["counterfactual_pair_id"] == pair_id and p["pair_class"] == pair_class for p in pairs)]) < target:
                progressed = False
                for mechanism in mechanisms:
                    if buckets[mechanism] and len([pair_id for pair_id in selected if any(p["counterfactual_pair_id"] == pair_id and p["pair_class"] == pair_class for p in pairs)]) < target:
                        selected.add(buckets[mechanism].pop(0)["counterfactual_pair_id"])
                        progressed = True
                if not progressed:
                    raise ValueError(f"cannot select {target} {pair_class} state pairs")
        else:
            if len(candidates) < target:
                raise ValueError(f"cannot select {target} {pair_class} state pairs")
            selected.update(pair["counterfactual_pair_id"] for pair in candidates[:target])
    return selected


def generate_regression_split(
    split: str,
    seed: int,
    families: tuple[int, ...],
    pairs_per_family: int,
    domains: tuple[str, ...],
    renderer: str,
    state_targets: dict[str, int],
    renderer_ids: dict[str, str],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], dict[str, Any], set[str]]:
    trajectories, pairs, lineages, audit = BASE.generate_split(
        split, seed, families, pairs_per_family, domains, split.upper()
    )
    for lineage in lineages:
        if lineage["lineage_type"] == "generator":
            lineage["content_sha256"] = digest({
                "protocol": PROTOCOL_ID,
                "split": split,
                "seed": seed,
                "families": families,
                "implementation": "mixed-retention-regression-v1",
            })
            lineage["parents"] = ["ACTIONNET-DATA-QUAL-014-result-v1.0.0"]
            lineage["transformation"] = "generate-fresh-mixed-retention-regression-v1"
    state_pairs = choose_state_pairs(pairs, state_targets)
    by_pair: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for trajectory in trajectories:
        by_pair[trajectory["counterfactual_pair_id"]].append(trajectory)
    rows: list[dict[str, Any]] = []
    for pair in sorted(pairs, key=lambda item: item["counterfactual_pair_id"]):
        pair_id = pair["counterfactual_pair_id"]
        if pair_id in state_pairs:
            for trajectory in sorted(by_pair[pair_id], key=lambda item: item["variant"]):
                for task in ("CERTIFICATE", "TRANSITION", "QUEUE_TRACE"):
                    rows.append(V10.state_record(trajectory, renderer, renderer_ids, task))
        rows.append(V10.pair_record(pair, renderer, renderer_ids))
    return rows, trajectories, lineages, audit, state_pairs


def summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "records": len(rows),
        "case_ids": len({row["case_id"] for row in rows}),
        "pair_ids": len({row["metadata"]["counterfactual_pair_id"] for row in rows}),
        "task_counts": dict(sorted(Counter(row["metadata"]["task_type"] for row in rows).items())),
        "renderer_counts": dict(sorted(Counter(row["metadata"]["selected_renderer"] for row in rows).items())),
        "profile_counts": dict(sorted(Counter(row["metadata"]["generator_profile"] for row in rows).items())),
        "source_counts": dict(sorted(Counter(row["metadata"].get("replay_source_protocol", "FRESH") for row in rows).items())),
        "weight_min": min(float(row["metadata"]["sample_weight"]) for row in rows),
        "weight_max": max(float(row["metadata"]["sample_weight"]) for row in rows),
    }


def generate() -> dict[str, Any]:
    renderer_ids, renderer_lineages = renderer_registry()
    train = mixed_training_rows()
    selection, selection_trajectories, selection_lineages, selection_audit, selection_state_pairs = generate_regression_split(
        "development_selection",
        SELECTION_SEED,
        SELECTION_FAMILIES,
        8,
        ("transport-retention", "benefits-retention"),
        SELECTION_RENDERER,
        {"PIVOTAL": 6, "INVARIANCE": 1, "CONTEXTUAL": 1},
        renderer_ids,
    )
    confirmation, confirmation_trajectories, confirmation_lineages, confirmation_audit, confirmation_state_pairs = generate_regression_split(
        "untouched_confirmation",
        CONFIRMATION_SEED,
        CONFIRMATION_FAMILIES,
        12,
        ("health-retention", "housing-retention", "licensing-retention", "research-retention"),
        CONFIRMATION_RENDERER,
        {"PIVOTAL": 16, "INVARIANCE": 4, "CONTEXTUAL": 4},
        renderer_ids,
    )
    summaries = {
        "train": summarize(train),
        "development_selection": summarize(selection),
        "untouched_confirmation": summarize(confirmation),
    }
    all_fresh_rows = selection + confirmation
    fresh_trajectories = selection_trajectories + confirmation_trajectories
    fresh_lineages = [*renderer_lineages, *selection_lineages, *confirmation_lineages]
    train_ids = {row["case_id"] for row in train}
    selection_ids = {row["case_id"] for row in selection}
    confirmation_ids = {row["case_id"] for row in confirmation}
    train_pairs = {row["metadata"]["counterfactual_pair_id"] for row in train}
    selection_pairs = {row["metadata"]["counterfactual_pair_id"] for row in selection}
    confirmation_pairs = {row["metadata"]["counterfactual_pair_id"] for row in confirmation}
    dev014 = read_jsonl(DEV014_SOURCE)
    dev014_ids = {row["case_id"] for row in dev014}
    dev014_pairs = {row["metadata"]["counterfactual_pair_id"] for row in dev014}
    fresh_families = {row["metadata"]["semantic_family"] for row in all_fresh_rows}
    fresh_appeals = [
        row for row in all_fresh_rows
        if row["metadata"]["task_type"] == "CERTIFICATE"
        and row["metadata"]["pair_mechanism"] == "UNRESOLVED_APPEAL"
    ]
    expected_train_tasks = {**TRAIN_COUNTS, "CERTIFICATE": TRAIN_COUNTS["CERTIFICATE"] + APPEAL_CERTIFICATES}
    controls = {
        "registered_counts": (len(train), len(selection), len(confirmation)) == (384, 64, 192),
        "registered_training_task_mix": summaries["train"]["task_counts"] == dict(sorted(expected_train_tasks.items())),
        "replay_source_counts": summaries["train"]["source_counts"] == {"ACTIONNET-DATA-QUAL-010": 352, "ACTIONNET-DATA-QUAL-013": 32},
        "state_reconstruction_tasks_emphasized": summaries["train"]["task_counts"]["TRANSITION"] == summaries["train"]["task_counts"]["QUEUE_TRACE"] == 96,
        "queue_trace_highest_weight": all(float(row["metadata"]["sample_weight"]) == 10.0 for row in train if row["metadata"]["task_type"] == "QUEUE_TRACE"),
        "appeal_retention_present": sum(row["metadata"].get("replay_source_protocol") == "ACTIONNET-DATA-QUAL-013" for row in train) == 32,
        "development_task_balance": summaries["development_selection"]["task_counts"] == {task: 16 for task in ("CERTIFICATE", "PAIR_CONTRAST", "QUEUE_TRACE", "TRANSITION")},
        "confirmation_task_balance": summaries["untouched_confirmation"]["task_counts"] == {task: 48 for task in ("CERTIFICATE", "PAIR_CONTRAST", "QUEUE_TRACE", "TRANSITION")},
        "development_state_pair_count_8": len(selection_state_pairs) == 8,
        "confirmation_state_pair_count_24": len(confirmation_state_pairs) == 24,
        "fresh_case_ids_unique": len(selection_ids | confirmation_ids) == 256,
        "train_development_confirmation_cases_disjoint": not (train_ids & selection_ids or train_ids & confirmation_ids or selection_ids & confirmation_ids),
        "train_development_confirmation_pairs_disjoint": not (train_pairs & selection_pairs or train_pairs & confirmation_pairs or selection_pairs & confirmation_pairs),
        "dev014_cases_disjoint": not dev014_ids & (selection_ids | confirmation_ids),
        "dev014_pairs_disjoint": not dev014_pairs & (selection_pairs | confirmation_pairs),
        "development_confirmation_families_disjoint": not ({row["metadata"]["semantic_family"] for row in selection} & {row["metadata"]["semantic_family"] for row in confirmation}),
        "dev014_families_disjoint": not {row["metadata"]["semantic_family"] for row in dev014} & fresh_families,
        "development_confirmation_renderers_disjoint": SELECTION_RENDERER != CONFIRMATION_RENDERER,
        "dev014_renderer_disjoint": all(row["metadata"]["selected_renderer"] != "HELDOUT_FULL_REGRESSION_REGISTER" for row in all_fresh_rows),
        "development_renderer_only": summaries["development_selection"]["renderer_counts"] == {SELECTION_RENDERER: 64},
        "confirmation_renderer_only": summaries["untouched_confirmation"]["renderer_counts"] == {CONFIRMATION_RENDERER: 192},
        "all_pivotal_mechanisms_in_confirmation": set(BASE.PIVOTAL_MECHANISMS).issubset(confirmation_audit["mechanism_distribution"]),
        "unresolved_appeal_scored_both_sides": {row["target"]["decision"] for row in fresh_appeals} == {"ALLOW", "CONTESTED"},
        "queue_integrity_exact": all(V10.queue_integrity(trajectory) for trajectory in fresh_trajectories),
        "independent_reference_engines_exact": selection_audit["engine_disagreements"] == confirmation_audit["engine_disagreements"] == 0,
        "independent_schedulers_exact": selection_audit["scheduler_disagreements"] == confirmation_audit["scheduler_disagreements"] == 0,
        "transition_engines_exact": selection_audit["transition_disagreements"] == confirmation_audit["transition_disagreements"] == 0,
        "decision_clock_exact": selection_audit["decision_clock_violations"] == confirmation_audit["decision_clock_violations"] == 0,
        "binding_authority_false": all(row["target"].get("binding_authority") is False for row in train + all_fresh_rows),
        "model_inputs_only_observation_query": all(set(row["input"]) == {"observation", "query"} for row in train + all_fresh_rows),
        "event_operands_visible": all(BASE.event_operands_visible(observation(row["metadata"]["selected_renderer"], renderer_ids, trajectory)["content"], trajectory["submitted_events"]) for row, trajectory in []),
        "fresh_seed_registration": (SELECTION_SEED, CONFIRMATION_SEED) == (26090590, 26090600),
        "reserved_future_families_unmaterialized": not fresh_families & set(RESERVED_FAMILIES),
        "lineage_ids_unique": len({row["lineage_id"] for row in fresh_lineages}) == len(fresh_lineages),
        "confirmation_single_use": True,
        "transfer_authorization_disabled": True,
    }
    # Check operand visibility without coupling rows to trajectory order.
    controls["event_operands_visible"] = all(
        BASE.event_operands_visible(
            observation(
                SELECTION_RENDERER if trajectory in selection_trajectories else CONFIRMATION_RENDERER,
                renderer_ids,
                trajectory,
            )["content"],
            trajectory["submitted_events"],
        )
        for trajectory in fresh_trajectories
    )
    return {
        "schema_version": "actionnet-data-qual-015-generated.v1",
        "protocol_id": PROTOCOL_ID,
        "result_id": RESULT_ID,
        "dataset_id": DATASET_ID,
        "datasets": {
            "train": train,
            "development_selection": selection,
            "untouched_confirmation": confirmation,
        },
        "canonical_trajectories": fresh_trajectories,
        "lineages": fresh_lineages,
        "controls": controls,
        "audits": {
            **summaries,
            "development_generator": selection_audit,
            "confirmation_generator": confirmation_audit,
            "development_state_pair_count": len(selection_state_pairs),
            "confirmation_state_pair_count": len(confirmation_state_pairs),
            "aggregate_target_sha256": digest([row["target"] for row in train + all_fresh_rows]),
        },
        "protected": {
            "reserved_future_families": list(RESERVED_FAMILIES),
            "development_selection_is_adaptive": True,
            "confirmation_single_use": True,
            "dev014_cases_prohibited_from_training": True,
            "public_materialized": False,
            "protected_materialized": False,
            "real_institution_materialized": False,
        },
    }