#!/usr/bin/env python3
"""Build fresh target-blind verified-hybrid development and confirmation splits."""

from __future__ import annotations

import hashlib
import importlib.util
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent
EXPERIMENTS = ROOT.parent
PARENT_PATH = EXPERIMENTS / "ACTIONNET-DATA-QUAL-017" / "actionnet017.py"

PROTOCOL_ID = "ACTIONNET-DATA-QUAL-018"
RESULT_ID = "ACTIONNET-DATA-QUAL-018-result-v1.0.0"
DATASET_ID = "ACTIONNET-VERIFIED-HYBRID-v18.0.0"
DEVELOPMENT_SEED = 26090680
CONFIRMATION_SEED = 26090690
DEVELOPMENT_FAMILIES = tuple(range(1000, 1002))
CONFIRMATION_FAMILIES = tuple(range(1020, 1024))
RESERVED_FAMILIES = tuple(range(1040, 1044))
DEVELOPMENT_RENDERER = "HELDOUT_VERIFIED_DEVELOPMENT_REGISTER"
CONFIRMATION_RENDERER = "HELDOUT_VERIFIED_CONFIRMATION_DOCKET"
EXPECTED_DEVELOPMENT_TASKS = {
    "CERTIFICATE": 16,
    "PAIR_CONTRAST": 16,
    "QUEUE_TRACE": 16,
    "TRANSITION": 16,
}
EXPECTED_CONFIRMATION_TASKS = {
    "CERTIFICATE": 48,
    "PAIR_CONTRAST": 48,
    "QUEUE_TRACE": 48,
    "TRANSITION": 48,
}


def _load_parent():
    spec = importlib.util.spec_from_file_location("actionnet017_parent_for_v18", PARENT_PATH)
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


def observation(style: str, renderer_ids: dict[str, str], trajectory: dict[str, Any]) -> dict[str, Any]:
    state = BASE.public_state(trajectory["initial_state"])
    clock = state["request"]["query_time"]
    events = trajectory["submitted_events"]
    if style == DEVELOPMENT_RENDERER:
        content = canonical({
            "domain": trajectory["domain"],
            "decision_clock": clock,
            "initial_state": state,
            "submitted_events_unordered": events,
            "canonical_order": ["time", "priority", "sequence", "event_id"],
            "execution_boundary": "inclusive",
            "late_event_disposition": "deferred",
            "mutation_rule": "only executed events may change state",
        })
        media_type = "application/json;profile=heldout-verified-development-register-v1"
    elif style == CONFIRMATION_RENDERER:
        entries = " || ".join(BASE.event_text(event) for event in events)
        content = (
            f"DOCKET<{trajectory['domain']}:VERIFIED_HYBRID>\n"
            f"INITIAL_RECORD::{canonical(state)}\n"
            f"SCHEDULED_ENTRIES::{entries}\n"
            f"DISPOSITION_TIME::{clock}\n"
            "ORDER::time,priority,sequence,event_id\n"
            "BOUNDARY::execute at or before disposition time; otherwise defer"
        )
        media_type = "text/plain;profile=heldout-verified-confirmation-docket-v1"
    else:
        raise ValueError(style)
    return {"renderer_lineage": renderer_ids[style], "media_type": media_type, "content": content}


V10.observation = observation


def renderer_registry() -> tuple[dict[str, str], list[dict[str, Any]]]:
    styles = (DEVELOPMENT_RENDERER, CONFIRMATION_RENDERER)
    mapping = {style: BASE.opaque("renderer", PROTOCOL_ID, style, "v1") for style in styles}
    records = [{
        "lineage_id": lineage,
        "lineage_type": "renderer",
        "version": "1.0.0",
        "content_sha256": digest({"style": style, "schema": "verified-hybrid-render-v18"}),
        "parents": [],
        "authority": "EDON Research Lab",
        "transformation": "render-verified-hybrid-evaluation-v1",
    } for style, lineage in mapping.items()]
    return mapping, records


def choose_state_pairs(pairs: list[dict[str, Any]], targets: dict[str, int]) -> set[str]:
    selected: set[str] = set()
    for pair_class, count in targets.items():
        candidates = [pair for pair in pairs if pair["pair_class"] == pair_class]
        if pair_class == "PIVOTAL":
            buckets: dict[str, list[dict[str, Any]]] = defaultdict(list)
            for pair in sorted(candidates, key=lambda item: item["counterfactual_pair_id"]):
                buckets[pair["intervention_family"]].append(pair)
            priority = [
                "DELAYED_EVIDENCE",
                "APPROVAL_WITHDRAWAL",
                "UNRESOLVED_APPEAL",
                "EVIDENCE_EXPIRY",
                "JURISDICTION_SHIFT",
            ]
            priority.extend(sorted(set(buckets) - set(priority)))
            while len(selected & {pair["counterfactual_pair_id"] for pair in candidates}) < count:
                progressed = False
                for mechanism in priority:
                    if buckets.get(mechanism) and len(
                        selected & {pair["counterfactual_pair_id"] for pair in candidates}
                    ) < count:
                        selected.add(buckets[mechanism].pop(0)["counterfactual_pair_id"])
                        progressed = True
                if not progressed:
                    raise ValueError(f"cannot select {count} {pair_class} state pairs")
        else:
            if len(candidates) < count:
                raise ValueError(f"cannot select {count} {pair_class} state pairs")
            selected.update(
                pair["counterfactual_pair_id"]
                for pair in sorted(candidates, key=lambda item: item["counterfactual_pair_id"])[:count]
            )
    return selected


def generate_split(
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
                "implementation": "fresh-target-blind-verified-hybrid-v1",
            })
            lineage["parents"] = ["ACTIONNET-DATA-QUAL-017-result-v1.0.0"]
            lineage["transformation"] = "generate-fresh-verified-hybrid-evaluation-v1"
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
                    row = V10.state_record(trajectory, renderer, renderer_ids, task)
                    row["metadata"]["replay_source_protocol"] = "FRESH"
                    rows.append(row)
        pair_row = V10.pair_record(pair, renderer, renderer_ids)
        pair_row["metadata"]["replay_source_protocol"] = "FRESH"
        rows.append(pair_row)
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
    development, dev_trajectories, dev_pairs, dev_lineages, dev_audit, dev_state_pairs = generate_split(
        "development_selection",
        DEVELOPMENT_SEED,
        DEVELOPMENT_FAMILIES,
        8,
        ("benefits-verified-development", "licensing-verified-development"),
        DEVELOPMENT_RENDERER,
        {"PIVOTAL": 6, "INVARIANCE": 1, "CONTEXTUAL": 1},
        renderer_ids,
    )
    confirmation, conf_trajectories, conf_pairs, conf_lineages, conf_audit, conf_state_pairs = generate_split(
        "untouched_confirmation",
        CONFIRMATION_SEED,
        CONFIRMATION_FAMILIES,
        12,
        (
            "health-verified-confirmation",
            "housing-verified-confirmation",
            "oversight-verified-confirmation",
            "research-verified-confirmation",
        ),
        CONFIRMATION_RENDERER,
        {"PIVOTAL": 16, "INVARIANCE": 4, "CONTEXTUAL": 4},
        renderer_ids,
    )
    summaries = {
        "development_selection": summarize(development),
        "untouched_confirmation": summarize(confirmation),
    }
    case_sets = [{row["case_id"] for row in rows} for rows in (development, confirmation)]
    pair_sets = [
        {row["metadata"]["counterfactual_pair_id"] for row in rows}
        for rows in (development, confirmation)
    ]
    family_sets = [
        {row["metadata"]["semantic_family"] for row in rows}
        for rows in (development, confirmation)
    ]
    all_rows = development + confirmation
    all_trajectories = dev_trajectories + conf_trajectories
    development_mechanisms = {
        row["metadata"].get("pair_mechanism")
        for row in development
        if row["metadata"]["task_type"] == "PAIR_CONTRAST"
    }
    delayed_development_certificates = [
        row for row in development
        if row["metadata"]["task_type"] == "CERTIFICATE"
        and row["metadata"].get("pair_mechanism") == "DELAYED_EVIDENCE"
    ]
    controls = {
        "registered_counts": (len(development), len(confirmation)) == (64, 192),
        "no_training_split": True,
        "development_task_balance": summaries["development_selection"]["task_counts"] == EXPECTED_DEVELOPMENT_TASKS,
        "confirmation_task_balance": summaries["untouched_confirmation"]["task_counts"] == EXPECTED_CONFIRMATION_TASKS,
        "all_records_fresh": all(row["metadata"].get("replay_source_protocol") == "FRESH" for row in all_rows),
        "development_contains_all_targeted_mechanisms": {
            "DELAYED_EVIDENCE", "APPROVAL_WITHDRAWAL", "UNRESOLVED_APPEAL",
            "EVIDENCE_EXPIRY", "JURISDICTION_SHIFT",
        }.issubset(development_mechanisms),
        "development_delayed_evidence_both_sides": {
            row["target"]["decision"] for row in delayed_development_certificates
        } == {"ALLOW", "ABSTAIN"},
        "all_pivotal_mechanisms_in_confirmation": set(BASE.PIVOTAL_MECHANISMS).issubset(
            conf_audit["mechanism_distribution"]
        ),
        "development_confirmation_case_ids_disjoint": not case_sets[0] & case_sets[1],
        "development_confirmation_pair_ids_disjoint": not pair_sets[0] & pair_sets[1],
        "development_confirmation_families_disjoint": not family_sets[0] & family_sets[1],
        "registered_family_allocation": family_sets == [set(DEVELOPMENT_FAMILIES), set(CONFIRMATION_FAMILIES)],
        "prior_validation_families_disjoint": not set().union(*family_sets) & set(range(780, 964)),
        "prior_validation_renderers_disjoint": {DEVELOPMENT_RENDERER, CONFIRMATION_RENDERER}.isdisjoint({
            "HELDOUT_FULL_REGRESSION_REGISTER",
            "HELDOUT_RETENTION_SELECTION_PACKET",
            "HELDOUT_RETENTION_CONFIRMATION_DOCKET",
            "HELDOUT_NARROW_SELECTION_REGISTER",
            "HELDOUT_NARROW_CONFIRMATION_DOCKET",
            "HELDOUT_COMPLETE_EXPOSURE_SELECTION_REGISTER",
            "HELDOUT_COMPLETE_EXPOSURE_CONFIRMATION_DOCKET",
        }),
        "queue_integrity_exact": all(V10.queue_integrity(trajectory) for trajectory in all_trajectories),
        "independent_reference_engines_exact": dev_audit["engine_disagreements"] == conf_audit["engine_disagreements"] == 0,
        "independent_schedulers_exact": dev_audit["scheduler_disagreements"] == conf_audit["scheduler_disagreements"] == 0,
        "transition_engines_exact": dev_audit["transition_disagreements"] == conf_audit["transition_disagreements"] == 0,
        "decision_clock_exact": dev_audit["decision_clock_violations"] == conf_audit["decision_clock_violations"] == 0,
        "binding_authority_false": all(row["target"].get("binding_authority") is False for row in all_rows),
        "model_inputs_only_observation_query": all(set(row["input"]) == {"observation", "query"} for row in all_rows),
        "verifier_inputs_constructible_without_target": all(
            set(row["input"]) == {"observation", "query"} and row["input"].get("observation")
            for row in all_rows
        ),
        "event_operands_visible": all(
            BASE.event_operands_visible(
                observation(
                    DEVELOPMENT_RENDERER if trajectory in dev_trajectories else CONFIRMATION_RENDERER,
                    renderer_ids,
                    trajectory,
                )["content"],
                trajectory["submitted_events"],
            )
            for trajectory in all_trajectories
        ),
        "fresh_seed_registration": (DEVELOPMENT_SEED, CONFIRMATION_SEED) == (26090680, 26090690),
        "reserved_future_families_unmaterialized": not set().union(*family_sets) & set(RESERVED_FAMILIES),
        "development_state_pair_count_8": len(dev_state_pairs) == 8,
        "confirmation_state_pair_count_24": len(conf_state_pairs) == 24,
        "confirmation_single_use": True,
        "target_blind_verification_required": True,
        "model_and_hybrid_scored_separately": True,
        "transfer_authorization_disabled": True,
    }
    lineages = [*renderer_lineages, *dev_lineages, *conf_lineages]
    controls["lineage_ids_unique"] = len({row["lineage_id"] for row in lineages}) == len(lineages)
    return {
        "schema_version": "actionnet-data-qual-018-generated.v1",
        "protocol_id": PROTOCOL_ID,
        "result_id": RESULT_ID,
        "dataset_id": DATASET_ID,
        "datasets": {
            "development_selection": development,
            "untouched_confirmation": confirmation,
        },
        "canonical_trajectories": all_trajectories,
        "lineages": lineages,
        "controls": controls,
        "audits": {
            **summaries,
            "development_generator": dev_audit,
            "confirmation_generator": conf_audit,
            "development_state_pair_count": len(dev_state_pairs),
            "confirmation_state_pair_count": len(conf_state_pairs),
            "aggregate_target_sha256": digest([row["target"] for row in all_rows]),
        },
        "protected": {
            "reserved_future_families": list(RESERVED_FAMILIES),
            "development_selection_is_adaptive": True,
            "confirmation_single_use": True,
            "verification_must_not_read_targets": True,
            "predecessor_confirmations_prohibited": True,
            "public_materialized": False,
            "protected_materialized": False,
            "real_institution_materialized": False,
        },
    }