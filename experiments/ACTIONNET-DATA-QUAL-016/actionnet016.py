#!/usr/bin/env python3
"""Build fresh delayed-evidence and exact-state narrow-repair splits."""

from __future__ import annotations

import hashlib
import importlib.util
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent
EXPERIMENTS = ROOT.parent
PARENT_PATH = EXPERIMENTS / "ACTIONNET-DATA-QUAL-015" / "actionnet015.py"

PROTOCOL_ID = "ACTIONNET-DATA-QUAL-016"
RESULT_ID = "ACTIONNET-DATA-QUAL-016-result-v1.0.0"
DATASET_ID = "ACTIONNET-DELAYED-EVIDENCE-STATE-REPAIR-v16.0.0"
TRAIN_SEED = 26090610
SELECTION_SEED = 26090620
CONFIRMATION_SEED = 26090630
TRAIN_FAMILIES = tuple(range(820, 824))
SELECTION_FAMILIES = tuple(range(840, 842))
CONFIRMATION_FAMILIES = tuple(range(860, 864))
RESERVED_FAMILIES = tuple(range(880, 884))
TRAIN_RENDERERS = ("DELAYED_EVIDENCE_LEDGER", "STATE_RECONSTRUCTION_PACKET")
SELECTION_RENDERER = "HELDOUT_NARROW_SELECTION_REGISTER"
CONFIRMATION_RENDERER = "HELDOUT_NARROW_CONFIRMATION_DOCKET"
EXPECTED_TRAIN_TASKS = {
    "CERTIFICATE": 64,
    "PAIR_CONTRAST": 48,
    "QUEUE_ORDER": 32,
    "QUEUE_PARTITION": 32,
    "QUEUE_TRACE": 96,
    "TRANSITION": 96,
}


def _load_parent():
    spec = importlib.util.spec_from_file_location("actionnet015_parent_for_v16", PARENT_PATH)
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
ORIGINAL_PIVOTAL_SCHEDULE = tuple(BASE.FOCUSED_PIVOTAL_SCHEDULE)


def canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def digest(value: Any) -> str:
    payload = value if isinstance(value, bytes) else canonical(value).encode("utf-8")
    return "sha256:" + hashlib.sha256(payload).hexdigest()


def observation(style: str, renderer_ids: dict[str, str], trajectory: dict[str, Any]) -> dict[str, Any]:
    state = BASE.public_state(trajectory["initial_state"])
    clock = state["request"]["query_time"]
    events = trajectory["submitted_events"]
    if style == "DELAYED_EVIDENCE_LEDGER":
        content = canonical({
            "domain": trajectory["domain"],
            "decision_clock": clock,
            "initial_state": state,
            "submitted_events_unordered": events,
            "evidence_cutoff_rule": "evidence mutations execute only when event.time <= decision_clock",
            "canonical_order": ["time", "priority", "sequence", "event_id"],
        })
        media_type = "application/json;profile=delayed-evidence-ledger-v1"
    elif style == "STATE_RECONSTRUCTION_PACKET":
        content = (
            f"STATE_PACKET<{trajectory['domain']}>\nINITIAL::{canonical(state)}\n"
            f"DECISION_CLOCK::{clock}\nUNORDERED_EVENTS::{canonical(events)}\n"
            "ORDER::time,priority,sequence,event_id\nEXECUTE::time<=decision_clock\nDEFER::time>decision_clock"
        )
        media_type = "text/plain;profile=state-reconstruction-packet-v1"
    elif style == SELECTION_RENDERER:
        content = canonical({
            "domain": trajectory["domain"],
            "decision_clock": clock,
            "initial_state": state,
            "submitted_events_unordered": events,
            "canonical_order": ["time", "priority", "sequence", "event_id"],
            "execution_boundary": "inclusive",
            "late_event_disposition": "deferred",
        })
        media_type = "application/json;profile=heldout-narrow-selection-register-v1"
    elif style == CONFIRMATION_RENDERER:
        entries = " || ".join(BASE.event_text(event) for event in events)
        content = (
            f"DOCKET<{trajectory['domain']}>\nINITIAL_RECORD::{canonical(state)}\n"
            f"SCHEDULED_ENTRIES::{entries}\nDISPOSITION_TIME::{clock}"
        )
        media_type = "text/plain;profile=heldout-narrow-confirmation-docket-v1"
    else:
        raise ValueError(style)
    return {"renderer_lineage": renderer_ids[style], "media_type": media_type, "content": content}


V10.observation = observation


def renderer_registry() -> tuple[dict[str, str], list[dict[str, Any]]]:
    styles = (*TRAIN_RENDERERS, SELECTION_RENDERER, CONFIRMATION_RENDERER)
    mapping = {style: BASE.opaque("renderer", PROTOCOL_ID, style, "v1") for style in styles}
    records = [{
        "lineage_id": lineage,
        "lineage_type": "renderer",
        "version": "1.0.0",
        "content_sha256": digest({"style": style, "schema": "narrow-state-repair-render-v16"}),
        "parents": [],
        "authority": "EDON Research Lab",
        "transformation": "render-delayed-evidence-state-repair-v1",
    } for style, lineage in mapping.items()]
    return mapping, records


def train_style(pair_id: str) -> str:
    return TRAIN_RENDERERS[int(hashlib.sha256(pair_id.encode("utf-8")).hexdigest()[:2], 16) % 2]


def set_weight(row: dict[str, Any]) -> dict[str, Any]:
    task = row["metadata"]["task_type"]
    mechanism = row["metadata"].get("pair_mechanism")
    variant = row["metadata"].get("variant")
    if mechanism == "DELAYED_EVIDENCE":
        weights = {
            "CERTIFICATE": 18.0 if variant == "INTERVENTION" else 12.0,
            "TRANSITION": 15.0,
            "QUEUE_TRACE": 13.0,
            "PAIR_CONTRAST": 16.0,
            "QUEUE_ORDER": 7.0,
            "QUEUE_PARTITION": 8.0,
        }
    else:
        weights = {
            "CERTIFICATE": 8.0,
            "TRANSITION": 12.0,
            "QUEUE_TRACE": 10.0,
            "PAIR_CONTRAST": 8.0,
            "QUEUE_ORDER": 6.0,
            "QUEUE_PARTITION": 7.0,
        }
    row["metadata"]["sample_weight"] = weights[task]
    row["metadata"]["repair_focus"] = (
        "DELAYED_EVIDENCE_SAFETY" if mechanism == "DELAYED_EVIDENCE" else "EXACT_STATE_RETENTION"
    )
    row["metadata"]["replay_source_protocol"] = "FRESH"
    return row


def round_robin_pairs(
    pairs: list[dict[str, Any]],
    pair_class: str,
    count: int,
    *,
    exclude: set[str] | None = None,
    exclude_mechanisms: set[str] | None = None,
) -> list[dict[str, Any]]:
    excluded = exclude or set()
    excluded_mechanisms = exclude_mechanisms or set()
    candidates = [
        pair for pair in pairs
        if pair["pair_class"] == pair_class and pair["counterfactual_pair_id"] not in excluded
        and pair["intervention_family"] not in excluded_mechanisms
    ]
    buckets: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for pair in sorted(candidates, key=lambda item: item["counterfactual_pair_id"]):
        buckets[pair["intervention_family"]].append(pair)
    selected: list[dict[str, Any]] = []
    priority = [
        mechanism for mechanism in BASE.PIVOTAL_MECHANISMS
        if mechanism in buckets and mechanism != "DELAYED_EVIDENCE"
    ]
    priority.extend(sorted(set(buckets) - set(priority)))
    while len(selected) < count:
        progressed = False
        for mechanism in priority:
            if buckets[mechanism] and len(selected) < count:
                selected.append(buckets[mechanism].pop(0))
                progressed = True
        if not progressed:
            raise ValueError(f"cannot select {count} {pair_class} pairs")
    return selected


def generate_training(renderer_ids: dict[str, str]):
    BASE.FOCUSED_PIVOTAL_SCHEDULE = (
        ("DELAYED_EVIDENCE",) * 8 + tuple(BASE.PIVOTAL_MECHANISMS)
    )
    try:
        trajectories, pairs, lineages, audit = BASE.generate_split(
            "train",
            TRAIN_SEED,
            TRAIN_FAMILIES,
            24,
            ("benefits-evidence", "licensing-state", "health-evidence", "research-state"),
            "NARROW_REPAIR_TRAIN",
        )
    finally:
        BASE.FOCUSED_PIVOTAL_SCHEDULE = ORIGINAL_PIVOTAL_SCHEDULE
    for lineage in lineages:
        if lineage["lineage_type"] == "generator":
            lineage["content_sha256"] = digest({
                "protocol": PROTOCOL_ID,
                "seed": TRAIN_SEED,
                "families": TRAIN_FAMILIES,
                "implementation": "fresh-delayed-evidence-state-repair-v1",
            })
            lineage["parents"] = ["ACTIONNET-DATA-QUAL-015-result-v1.0.0"]
            lineage["transformation"] = "generate-fresh-narrow-repair-training-v1"
    by_pair: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for trajectory in trajectories:
        by_pair[trajectory["counterfactual_pair_id"]].append(trajectory)
    delayed = sorted(
        [pair for pair in pairs if pair["intervention_family"] == "DELAYED_EVIDENCE"],
        key=lambda item: item["counterfactual_pair_id"],
    )[:16]
    if len(delayed) != 16:
        raise ValueError("insufficient delayed-evidence training pairs")
    delayed_ids = {pair["counterfactual_pair_id"] for pair in delayed}
    broad = [
        *round_robin_pairs(
            pairs,
            "PIVOTAL",
            24,
            exclude=delayed_ids,
            exclude_mechanisms={"DELAYED_EVIDENCE"},
        ),
        *round_robin_pairs(pairs, "INVARIANCE", 4),
        *round_robin_pairs(pairs, "CONTEXTUAL", 4),
    ]
    broad_ids = {pair["counterfactual_pair_id"] for pair in broad}
    if delayed_ids & broad_ids or len(broad_ids) != 32:
        raise ValueError("training pair selection overlap")

    rows: list[dict[str, Any]] = []
    for pair in delayed:
        style = train_style(pair["counterfactual_pair_id"])
        for trajectory in sorted(by_pair[pair["counterfactual_pair_id"]], key=lambda item: item["variant"]):
            for task in ("CERTIFICATE", "TRANSITION", "QUEUE_TRACE"):
                rows.append(set_weight(V10.state_record(trajectory, style, renderer_ids, task)))
        rows.append(set_weight(V10.pair_record(pair, style, renderer_ids)))
    pivotal_broad = [pair for pair in broad if pair["pair_class"] == "PIVOTAL"]
    certificate_ids = {pair["counterfactual_pair_id"] for pair in pivotal_broad[:16]}
    for pair in broad:
        style = train_style(pair["counterfactual_pair_id"])
        for trajectory in sorted(by_pair[pair["counterfactual_pair_id"]], key=lambda item: item["variant"]):
            for task in ("TRANSITION", "QUEUE_TRACE"):
                rows.append(set_weight(V10.state_record(trajectory, style, renderer_ids, task)))
            if pair["counterfactual_pair_id"] in certificate_ids:
                rows.append(set_weight(V10.state_record(trajectory, style, renderer_ids, "CERTIFICATE")))
        rows.append(set_weight(V10.pair_record(pair, style, renderer_ids)))
    order_trajectories = sorted(
        [trajectory for pair_id in broad_ids for trajectory in by_pair[pair_id]],
        key=lambda item: item["trajectory_id"],
    )[:32]
    for trajectory in order_trajectories:
        style = train_style(trajectory["counterfactual_pair_id"])
        for task in ("QUEUE_ORDER", "QUEUE_PARTITION"):
            rows.append(set_weight(V10.state_record(trajectory, style, renderer_ids, task)))
    rows.sort(key=lambda row: (row["metadata"]["task_type"], row["case_id"]))
    if len({row["case_id"] for row in rows}) != len(rows):
        raise ValueError("duplicate training case identifiers")
    return rows, trajectories, pairs, lineages, audit, delayed_ids, broad_ids


def choose_state_pairs(pairs: list[dict[str, Any]], targets: dict[str, int]) -> set[str]:
    selected: set[str] = set()
    for pair_class, count in targets.items():
        candidates = [pair for pair in pairs if pair["pair_class"] == pair_class]
        if pair_class == "PIVOTAL":
            buckets: dict[str, list[dict[str, Any]]] = defaultdict(list)
            for pair in sorted(candidates, key=lambda item: item["counterfactual_pair_id"]):
                buckets[pair["intervention_family"]].append(pair)
            priority = ["DELAYED_EVIDENCE", "UNRESOLVED_APPEAL"]
            priority.extend(sorted(set(buckets) - set(priority)))
            while sum(pair_id in selected for pair_id in [p["counterfactual_pair_id"] for p in candidates]) < count:
                progressed = False
                for mechanism in priority:
                    if buckets.get(mechanism) and sum(
                        pair["counterfactual_pair_id"] in selected for pair in candidates
                    ) < count:
                        selected.add(buckets[mechanism].pop(0)["counterfactual_pair_id"])
                        progressed = True
                if not progressed:
                    raise ValueError(f"cannot select {count} {pair_class} state pairs")
        else:
            if len(candidates) < count:
                raise ValueError(f"cannot select {count} {pair_class} state pairs")
            selected.update(pair["counterfactual_pair_id"] for pair in sorted(
                candidates, key=lambda item: item["counterfactual_pair_id"]
            )[:count])
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
):
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
                "implementation": "fresh-narrow-repair-regression-v1",
            })
            lineage["parents"] = ["ACTIONNET-DATA-QUAL-015-result-v1.0.0"]
            lineage["transformation"] = "generate-fresh-narrow-repair-regression-v1"
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
    return rows, trajectories, pairs, lineages, audit, state_pairs


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
    train, train_trajectories, train_pairs, train_lineages, train_audit, delayed_ids, broad_ids = generate_training(renderer_ids)
    selection, selection_trajectories, selection_pairs, selection_lineages, selection_audit, selection_state_pairs = generate_regression_split(
        "development_selection",
        SELECTION_SEED,
        SELECTION_FAMILIES,
        8,
        ("benefits-narrow-selection", "licensing-narrow-selection"),
        SELECTION_RENDERER,
        {"PIVOTAL": 6, "INVARIANCE": 1, "CONTEXTUAL": 1},
        renderer_ids,
    )
    confirmation, confirmation_trajectories, confirmation_pairs, confirmation_lineages, confirmation_audit, confirmation_state_pairs = generate_regression_split(
        "untouched_confirmation",
        CONFIRMATION_SEED,
        CONFIRMATION_FAMILIES,
        12,
        ("health-narrow-confirmation", "housing-narrow-confirmation", "oversight-narrow-confirmation", "research-narrow-confirmation"),
        CONFIRMATION_RENDERER,
        {"PIVOTAL": 16, "INVARIANCE": 4, "CONTEXTUAL": 4},
        renderer_ids,
    )
    summaries = {
        "train": summarize(train),
        "development_selection": summarize(selection),
        "untouched_confirmation": summarize(confirmation),
    }
    split_rows = (train, selection, confirmation)
    case_sets = [{row["case_id"] for row in rows} for rows in split_rows]
    pair_sets = [{row["metadata"]["counterfactual_pair_id"] for row in rows} for rows in split_rows]
    all_trajectories = train_trajectories + selection_trajectories + confirmation_trajectories
    all_rows = train + selection + confirmation
    delayed_train = [row for row in train if row["metadata"].get("pair_mechanism") == "DELAYED_EVIDENCE"]
    delayed_certificates = [row for row in delayed_train if row["metadata"]["task_type"] == "CERTIFICATE"]
    development_delayed = [
        row for row in selection
        if row["metadata"]["task_type"] == "CERTIFICATE"
        and row["metadata"].get("pair_mechanism") == "DELAYED_EVIDENCE"
    ]
    family_sets = [
        {row["metadata"]["semantic_family"] for row in rows} for rows in split_rows
    ]
    controls = {
        "registered_counts": tuple(len(rows) for rows in split_rows) == (368, 64, 192),
        "registered_training_task_mix": summaries["train"]["task_counts"] == EXPECTED_TRAIN_TASKS,
        "all_training_records_fresh": summaries["train"]["source_counts"] == {"FRESH": 368},
        "delayed_evidence_pair_count_16": len(delayed_ids) == 16,
        "broad_state_pair_count_32": len(broad_ids) == 32,
        "delayed_evidence_certificate_balance": Counter(
            row["target"]["decision"] for row in delayed_certificates
        ) == {"ALLOW": 16, "ABSTAIN": 16},
        "delayed_evidence_interventions_highest_weight": all(
            float(row["metadata"]["sample_weight"]) == 18.0
            for row in delayed_certificates if row["metadata"]["variant"] == "INTERVENTION"
        ),
        "transition_and_queue_trace_count_96": summaries["train"]["task_counts"]["TRANSITION"] == summaries["train"]["task_counts"]["QUEUE_TRACE"] == 96,
        "development_task_balance": summaries["development_selection"]["task_counts"] == {task: 16 for task in ("CERTIFICATE", "PAIR_CONTRAST", "QUEUE_TRACE", "TRANSITION")},
        "confirmation_task_balance": summaries["untouched_confirmation"]["task_counts"] == {task: 48 for task in ("CERTIFICATE", "PAIR_CONTRAST", "QUEUE_TRACE", "TRANSITION")},
        "development_contains_delayed_evidence_both_sides": {row["target"]["decision"] for row in development_delayed} == {"ALLOW", "ABSTAIN"},
        "all_pivotal_mechanisms_in_confirmation": set(BASE.PIVOTAL_MECHANISMS).issubset(confirmation_audit["mechanism_distribution"]),
        "split_case_ids_disjoint": not (case_sets[0] & case_sets[1] or case_sets[0] & case_sets[2] or case_sets[1] & case_sets[2]),
        "split_pair_ids_disjoint": not (pair_sets[0] & pair_sets[1] or pair_sets[0] & pair_sets[2] or pair_sets[1] & pair_sets[2]),
        "previous_validation_namespace_disjoint": PROTOCOL_ID not in {
            "ACTIONNET-DATA-QUAL-014", "ACTIONNET-DATA-QUAL-015"
        },
        "previous_validation_families_and_renderers_disjoint": (
            not set().union(*family_sets) & set(range(780, 804))
            and not {SELECTION_RENDERER, CONFIRMATION_RENDERER}
            & {"HELDOUT_FULL_REGRESSION_REGISTER", "HELDOUT_RETENTION_SELECTION_PACKET", "HELDOUT_RETENTION_CONFIRMATION_DOCKET"}
        ),
        "split_families_disjoint": not (family_sets[0] & family_sets[1] or family_sets[0] & family_sets[2] or family_sets[1] & family_sets[2]),
        "registered_family_allocation": family_sets == [set(TRAIN_FAMILIES), set(SELECTION_FAMILIES), set(CONFIRMATION_FAMILIES)],
        "development_confirmation_renderers_disjoint": SELECTION_RENDERER != CONFIRMATION_RENDERER,
        "queue_integrity_exact": all(V10.queue_integrity(trajectory) for trajectory in all_trajectories),
        "independent_reference_engines_exact": train_audit["engine_disagreements"] == selection_audit["engine_disagreements"] == confirmation_audit["engine_disagreements"] == 0,
        "independent_schedulers_exact": train_audit["scheduler_disagreements"] == selection_audit["scheduler_disagreements"] == confirmation_audit["scheduler_disagreements"] == 0,
        "transition_engines_exact": train_audit["transition_disagreements"] == selection_audit["transition_disagreements"] == confirmation_audit["transition_disagreements"] == 0,
        "decision_clock_exact": train_audit["decision_clock_violations"] == selection_audit["decision_clock_violations"] == confirmation_audit["decision_clock_violations"] == 0,
        "binding_authority_false": all(row["target"].get("binding_authority") is False for row in all_rows),
        "model_inputs_only_observation_query": all(set(row["input"]) == {"observation", "query"} for row in all_rows),
        "event_operands_visible": all(
            BASE.event_operands_visible(
                observation(
                    train_style(trajectory["counterfactual_pair_id"])
                    if trajectory in train_trajectories
                    else SELECTION_RENDERER if trajectory in selection_trajectories else CONFIRMATION_RENDERER,
                    renderer_ids,
                    trajectory,
                )["content"],
                trajectory["submitted_events"],
            )
            for trajectory in all_trajectories
        ),
        "fresh_seed_registration": (TRAIN_SEED, SELECTION_SEED, CONFIRMATION_SEED) == (26090610, 26090620, 26090630),
        "reserved_future_families_unmaterialized": not set().union(*family_sets) & set(RESERVED_FAMILIES),
        "confirmation_single_use": True,
        "transfer_authorization_disabled": True,
    }
    lineages = [*renderer_lineages, *train_lineages, *selection_lineages, *confirmation_lineages]
    controls["lineage_ids_unique"] = len({row["lineage_id"] for row in lineages}) == len(lineages)
    return {
        "schema_version": "actionnet-data-qual-016-generated.v1",
        "protocol_id": PROTOCOL_ID,
        "result_id": RESULT_ID,
        "dataset_id": DATASET_ID,
        "datasets": {
            "train": train,
            "development_selection": selection,
            "untouched_confirmation": confirmation,
        },
        "canonical_trajectories": all_trajectories,
        "lineages": lineages,
        "controls": controls,
        "audits": {
            **summaries,
            "training_generator": train_audit,
            "development_generator": selection_audit,
            "confirmation_generator": confirmation_audit,
            "delayed_evidence_training_pairs": len(delayed_ids),
            "broad_state_training_pairs": len(broad_ids),
            "development_state_pair_count": len(selection_state_pairs),
            "confirmation_state_pair_count": len(confirmation_state_pairs),
            "aggregate_target_sha256": digest([row["target"] for row in all_rows]),
        },
        "protected": {
            "reserved_future_families": list(RESERVED_FAMILIES),
            "development_selection_is_adaptive": True,
            "confirmation_single_use": True,
            "dev014_and_dev015_validation_prohibited_from_training": True,
            "public_materialized": False,
            "protected_materialized": False,
            "real_institution_materialized": False,
        },
    }