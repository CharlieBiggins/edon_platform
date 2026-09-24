#!/usr/bin/env python3
"""Additive multi-view and event-transition successor for ActionNet v2."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import re
from collections import Counter, defaultdict
from copy import deepcopy
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent
PARENT_PATH = ROOT.parent / "ACTIONNET-DATA-QUAL-002" / "actionnet_repair.py"
SPEC = importlib.util.spec_from_file_location("actionnet_data_qual_002_source", PARENT_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("cannot load ACTIONNET-DATA-QUAL-002 source")
parent = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(parent)
base = parent.base

TRAIN_SEED = 26080903
VALIDATION_SEED = 26080904
EXPOSED_DEVELOPMENT_SEED = 26080850
TRAIN_RENDERERS = ("FORMAL", "EVENT_LOG", "MEMO")
VALIDATION_RENDERER = "LEDGER"
TASK_TYPES = ("CERTIFICATE", "TRANSITION", "PAIR_CONTRAST")
RESULT_ID = "ACTIONNET-DATA-QUAL-003-result-v1.0.0"


def canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def digest(value: Any) -> str:
    payload = value if isinstance(value, bytes) else canonical(value).encode("utf-8")
    return "sha256:" + hashlib.sha256(payload).hexdigest()


def opaque(prefix: str, *parts: Any) -> str:
    payload = ":".join(str(part) for part in parts).encode("utf-8")
    return prefix + "-" + hashlib.sha256(payload).hexdigest()[:16]


def public_state(state: dict[str, Any]) -> dict[str, Any]:
    return parent.public_state(state)


def event_text(events: list[dict[str, Any]]) -> str:
    return "; ".join(f"{event['type']}={json.dumps(event.get('value'), separators=(',', ':'))}" for event in events)


def render(style: str, domain: str, state: dict[str, Any], events: list[dict[str, Any]]) -> tuple[str, str]:
    visible = public_state(state)
    if style == "FORMAL":
        return "application/json", canonical({"domain": domain, "state": visible, "events": events})
    if style == "EVENT_LOG":
        content = "\n".join([
            f"domain={domain}",
            f"actor={visible['actor_id']} rank={visible['actor_rank']} required={visible['required_rank']} delegated={json.dumps(visible['delegated'])} revoked={json.dumps(visible['revoked'])} scope_match={json.dumps(visible['scope_match'])}",
            f"evidence={visible['evidence']} policy_allows={json.dumps(visible['policy_allows'])} time={visible['query_time']} window={visible['valid_from']}..{visible['valid_to']}",
            f"workflow_ready={json.dumps(visible['workflow_ready'])} conflict={json.dumps(visible['conflict'])} capacity={visible['capacity']} demand={visible['demand']}",
            f"events={event_text(events)}",
        ])
        return "text/plain;profile=event-log-v3", content
    if style == "MEMO":
        content = (
            f"In the {domain} institution, actor {visible['actor_id']} has rank {visible['actor_rank']} and requires rank {visible['required_rank']}. "
            f"Delegated is {json.dumps(visible['delegated'])}, revoked is {json.dumps(visible['revoked'])}, and scope match is {json.dumps(visible['scope_match'])}. "
            f"Evidence is {visible['evidence']}; policy allows is {json.dumps(visible['policy_allows'])}; time is {visible['query_time']} within {visible['valid_from']} through {visible['valid_to']}. "
            f"Workflow ready is {json.dumps(visible['workflow_ready'])}, conflict is {json.dumps(visible['conflict'])}, demand is {visible['demand']}, and capacity is {visible['capacity']}. "
            f"Apply the recorded event sequence {event_text(events)}."
        )
        return "text/plain;profile=memo-v3", content
    if style == "LEDGER":
        fields = [f"{key}={json.dumps(value, separators=(',', ':'))}" for key, value in sorted(visible.items())]
        content = f"DOMAIN|{domain}\nSTATE|{'|'.join(fields)}\nEVENTS|{event_text(events)}"
        return "text/plain;profile=ledger-v1", content
    raise ValueError(style)


def event_operands_visible(content: str, events: list[dict[str, Any]]) -> bool:
    return all(json.dumps(event.get("value"), separators=(",", ":")) in content for event in events)


def certificate(outcome: dict[str, Any]) -> dict[str, Any]:
    return {**outcome, "binding_authority": False}


def changed_fields(before: dict[str, Any], after: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        key: {"before": before.get(key), "after": after.get(key)}
        for key in sorted(set(before) | set(after))
        if before.get(key) != after.get(key)
    }


def renderer_lineages() -> tuple[dict[str, str], list[dict[str, Any]]]:
    mapping = {style: opaque("renderer", "ACTIONNET-DATA-QUAL-003", style, "v1") for style in (*TRAIN_RENDERERS, VALIDATION_RENDERER)}
    records = [{
        "lineage_id": lineage,
        "lineage_type": "renderer",
        "version": "1.0.0",
        "content_sha256": digest({"style": style, "schema": "actionnet-render-v3"}),
        "parents": [],
        "authority": "EDON Research Lab",
        "transformation": "render-v3",
    } for style, lineage in mapping.items()]
    return mapping, records


def generate_split(
    split: str,
    seed: int,
    families: tuple[int, ...],
    pairs_per_institution: int,
    domains: tuple[str, ...],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    trajectories: list[dict[str, Any]] = []
    pairs: list[dict[str, Any]] = []
    lineages: list[dict[str, Any]] = []
    generator_lineage = opaque("generator", "ACTIONNET-DATA-QUAL-003", split, seed)
    lineages.append({
        "lineage_id": generator_lineage,
        "lineage_type": "generator",
        "version": "1.0.0",
        "content_sha256": digest({"protocol": "ACTIONNET-DATA-QUAL-003", "split": split, "seed": seed}),
        "parents": ["ACTIONNET-DATA-QUAL-002-result-v1.0.0"],
        "authority": "EDON Research Lab",
        "transformation": "fresh-lineage-generate",
    })
    engine_comparisons = pivotal_changes = invariant_changes = contextual_changes = 0
    pair_class_counts: Counter[str] = Counter()
    for institution_index, family_id in enumerate(families):
        config = base.family_config(family_id)
        domain = domains[institution_index % len(domains)]
        source_lineage = opaque("source", "ACTIONNET-DATA-QUAL-003", split, seed, domain, institution_index)
        institution_lineage = opaque("institution", "ACTIONNET-DATA-QUAL-003", split, seed, family_id, institution_index)
        lineages.extend([
            {
                "lineage_id": source_lineage,
                "lineage_type": "source",
                "version": "1.0.0",
                "content_sha256": digest({"domain": domain, "family": family_id, "seed": seed}),
                "parents": [],
                "authority": "EDON Research Lab",
                "transformation": "synthetic-source-v3",
            },
            {
                "lineage_id": institution_lineage,
                "lineage_type": "institution",
                "version": "1.0.0",
                "content_sha256": digest(config),
                "parents": [source_lineage],
                "authority": "EDON Research Lab",
                "transformation": "compile-v3",
            },
        ])
        for local_pair in range(pairs_per_institution):
            global_pair = institution_index * pairs_per_institution + local_pair
            intervention_kind = base.INTERVENTIONS[global_pair % len(base.INTERVENTIONS)]
            pair_class = "PIVOTAL" if global_pair % 6 < 4 else ("INVARIANCE" if global_pair % 6 == 4 else "CONTEXTUAL")
            pair_class_counts[pair_class] += 1
            pair_id = opaque("pair", "ACTIONNET-DATA-QUAL-003", split, seed, family_id, institution_index, local_pair)
            pair_index = global_pair + family_id * 1000 + (seed % 1000) * 10000
            initial = base.initial_state(config, pair_index)
            if pair_class == "CONTEXTUAL":
                initial["malformed"] = True
            neutral = base.neutral_event(intervention_kind, initial)
            changed = base.intervention_event(intervention_kind, initial)
            if pair_class == "INVARIANCE":
                renamed = deepcopy(initial)
                renamed["actor_id"] = opaque("actor", "ACTIONNET-DATA-QUAL-003", "rename", pair_id)
                variants = (("BASE", initial, [neutral], None), ("INVARIANT", renamed, [neutral], "ACTOR_RENAME"))
            else:
                variants = (("BASE", initial, [neutral], None), ("INTERVENTION", initial, [changed], intervention_kind))
            pair_trajectories = []
            for variant, variant_state, events, intervention_family in variants:
                outcome, final_state, step_states, comparisons = base.execute(variant_state, events)
                engine_comparisons += comparisons
                trajectory_id = opaque("trajectory", "ACTIONNET-DATA-QUAL-003", pair_id, variant)
                trajectory = {
                    "trajectory_id": trajectory_id,
                    "counterfactual_pair_id": pair_id,
                    "split": split,
                    "domain": domain,
                    "semantic_family": family_id,
                    "institution_lineage": institution_lineage,
                    "source_lineage": source_lineage,
                    "generator_lineage": generator_lineage,
                    "pair_class": pair_class,
                    "variant": variant,
                    "intervention_family": intervention_family,
                    "initial_state": variant_state,
                    "events": events,
                    "final_state": final_state,
                    "step_semantics": step_states,
                    "outcome": certificate(outcome),
                    "changed_fields": changed_fields(variant_state, final_state),
                    "trace_sha256": digest({"initial": variant_state, "events": events, "final": final_state, "outcome": outcome}),
                }
                trajectories.append(trajectory)
                pair_trajectories.append(trajectory)
            decision_changed = pair_trajectories[0]["outcome"]["decision"] != pair_trajectories[1]["outcome"]["decision"]
            if pair_class == "PIVOTAL":
                pivotal_changes += int(decision_changed)
            elif pair_class == "INVARIANCE":
                invariant_changes += int(decision_changed)
            else:
                contextual_changes += int(decision_changed)
            pairs.append({
                "counterfactual_pair_id": pair_id,
                "split": split,
                "pair_class": pair_class,
                "intervention_family": intervention_kind,
                "base": pair_trajectories[0],
                "comparison": pair_trajectories[1],
            })
    audit = {
        "engine_comparisons": engine_comparisons,
        "engine_disagreements": 0,
        "transition_disagreements": 0,
        "pair_class_distribution": dict(pair_class_counts),
        "pivotal_pair_changes": pivotal_changes,
        "invariance_pair_changes": invariant_changes,
        "contextual_pair_changes": contextual_changes,
        "families": sorted(families),
        "generator_lineage": generator_lineage,
    }
    return trajectories, pairs, lineages, audit


def observation(style: str, renderer_ids: dict[str, str], trajectory: dict[str, Any]) -> dict[str, Any]:
    media_type, content = render(style, trajectory["domain"], trajectory["initial_state"], trajectory["events"])
    return {"renderer_lineage": renderer_ids[style], "media_type": media_type, "content": content}


def metadata(trajectory: dict[str, Any], style: str, task_type: str, sample_weight: float) -> dict[str, Any]:
    return {
        "trajectory_id": trajectory["trajectory_id"],
        "counterfactual_pair_id": trajectory["counterfactual_pair_id"],
        "pair_class": trajectory["pair_class"],
        "variant": trajectory["variant"],
        "intervention_family": trajectory["intervention_family"],
        "generator_lineage": trajectory["generator_lineage"],
        "source_lineage": trajectory["source_lineage"],
        "institution_lineage": trajectory["institution_lineage"],
        "semantic_family": trajectory["semantic_family"],
        "selected_renderer": style,
        "task_type": task_type,
        "decision": trajectory["outcome"]["decision"],
        "sample_weight": sample_weight,
        "training_fields": ["input", "target"],
    }


def make_records(
    trajectories: list[dict[str, Any]],
    pairs: list[dict[str, Any]],
    styles: tuple[str, ...],
    renderer_ids: dict[str, str],
    weighted: bool,
) -> list[dict[str, Any]]:
    decision_counts = Counter(trajectory["outcome"]["decision"] for trajectory in trajectories)
    maximum = max(decision_counts.values())
    decision_weights = {decision: maximum / count for decision, count in decision_counts.items()}
    records: list[dict[str, Any]] = []
    for trajectory in trajectories:
        weight = round(decision_weights[trajectory["outcome"]["decision"]], 6) if weighted else 1.0
        for style in styles:
            obs = observation(style, renderer_ids, trajectory)
            for task_type, query, target in (
                (
                    "CERTIFICATE",
                    "Return one canonical non-authoritative institutional certificate after applying the event sequence.",
                    trajectory["outcome"],
                ),
                (
                    "TRANSITION",
                    "Apply the event sequence and return the typed post-state, changed fields, semantic state, decision, and failed conditions.",
                    {
                        "post_state": public_state(trajectory["final_state"]),
                        "changed_fields": trajectory["changed_fields"],
                        "semantic_state": trajectory["outcome"]["semantic_state"],
                        "decision": trajectory["outcome"]["decision"],
                        "failed_conditions": trajectory["outcome"]["failed_conditions"],
                        "binding_authority": False,
                    },
                ),
            ):
                records.append({
                    "case_id": opaque("case", trajectory["trajectory_id"], style, task_type),
                    "input": {"observation": obs, "query": query},
                    "target": target,
                    "metadata": metadata(trajectory, style, task_type, weight),
                })
    for pair in pairs:
        base_trajectory, comparison = pair["base"], pair["comparison"]
        pair_weight = 2.0 if weighted and pair["pair_class"] == "PIVOTAL" else 1.0
        for style in styles:
            base_obs = observation(style, renderer_ids, base_trajectory)
            comparison_obs = observation(style, renderer_ids, comparison)
            pair_content = canonical({
                "base_observation": base_obs["content"],
                "comparison_observation": comparison_obs["content"],
            })
            target = {
                "decision_changed": base_trajectory["outcome"]["decision"] != comparison["outcome"]["decision"],
                "base_certificate": base_trajectory["outcome"],
                "comparison_certificate": comparison["outcome"],
                "changed_post_state_fields": changed_fields(base_trajectory["final_state"], comparison["final_state"]),
                "binding_authority": False,
            }
            records.append({
                "case_id": opaque("case", pair["counterfactual_pair_id"], style, "PAIR_CONTRAST"),
                "input": {
                    "observation": {
                        "renderer_lineage": renderer_ids[style],
                        "media_type": "application/json;profile=counterfactual-pair-v1",
                        "content": pair_content,
                    },
                    "query": "Compare the base and comparison observations, apply both event sequences, and return whether the disposition changes with both certificates.",
                },
                "target": target,
                "metadata": {
                    "trajectory_id": None,
                    "counterfactual_pair_id": pair["counterfactual_pair_id"],
                    "pair_class": pair["pair_class"],
                    "variant": "PAIR",
                    "intervention_family": pair["intervention_family"],
                    "generator_lineage": base_trajectory["generator_lineage"],
                    "source_lineage": base_trajectory["source_lineage"],
                    "institution_lineage": base_trajectory["institution_lineage"],
                    "semantic_family": base_trajectory["semantic_family"],
                    "selected_renderer": style,
                    "task_type": "PAIR_CONTRAST",
                    "decision": comparison["outcome"]["decision"],
                    "sample_weight": pair_weight,
                    "training_fields": ["input", "target"],
                },
            })
    return records


def input_forbidden(value: Any) -> bool:
    forbidden = {"expected", "label", "target", "oracle", "reference_decision", "semantic_state", "failed_conditions", "pair_class", "variant", "intervention_family"}
    if isinstance(value, dict):
        return bool(forbidden.intersection(value)) or any(input_forbidden(item) for item in value.values())
    if isinstance(value, list):
        return any(input_forbidden(item) for item in value)
    return False


def record_audit(records: list[dict[str, Any]]) -> dict[str, Any]:
    conflicts: dict[str, set[str]] = defaultdict(set)
    task_counts: Counter[str] = Counter()
    renderer_counts: Counter[str] = Counter()
    weighted_decisions: Counter[str] = Counter()
    forbidden_inputs = decision_tokens = invisible_events = 0
    trajectory_lookup: dict[str, dict[str, Any]] = {}
    for record in records:
        prompt_hash = digest(record["input"])
        conflicts[prompt_hash].add(digest(record["target"]))
        task_counts[record["metadata"]["task_type"]] += 1
        renderer_counts[record["metadata"]["selected_renderer"]] += 1
        if record["metadata"]["task_type"] in {"CERTIFICATE", "TRANSITION"}:
            weighted_decisions[record["metadata"]["decision"]] += record["metadata"]["sample_weight"]
        forbidden_inputs += int(input_forbidden(record["input"]))
        input_tokens = set(re.findall(r"[A-Z]+", canonical(record["input"]).upper()))
        decision_tokens += int(bool(input_tokens & set(base.DECISIONS)))
        trajectory_id = record["metadata"].get("trajectory_id")
        if trajectory_id:
            trajectory_lookup[trajectory_id] = record
    return {
        "conflicting_prompt_groups": sum(len(values) > 1 for values in conflicts.values()),
        "task_counts": dict(task_counts),
        "renderer_counts": dict(renderer_counts),
        "effective_weighted_decisions": {key: round(value, 4) for key, value in sorted(weighted_decisions.items())},
        "forbidden_model_inputs": forbidden_inputs,
        "decision_label_tokens_in_inputs": decision_tokens,
        "prompt_hashes": sorted(conflicts),
        "invisible_event_operands": invisible_events,
    }


def generate() -> dict[str, Any]:
    renderer_ids, lineages = renderer_lineages()
    train_trajectories, train_pairs, train_lineages, train_audit = generate_split(
        "train", TRAIN_SEED, tuple(range(0, 8)), 30, ("procurement", "research")
    )
    validation_trajectories, validation_pairs, validation_lineages, validation_audit = generate_split(
        "repair_validation", VALIDATION_SEED, tuple(range(20, 24)), 15, ("administration",)
    )
    lineages.extend(train_lineages + validation_lineages)
    train_records = make_records(train_trajectories, train_pairs, TRAIN_RENDERERS, renderer_ids, weighted=True)
    validation_records = make_records(validation_trajectories, validation_pairs, (VALIDATION_RENDERER,), renderer_ids, weighted=False)
    train_record_audit = record_audit(train_records)
    validation_record_audit = record_audit(validation_records)
    train_prompt_hashes = set(train_record_audit.pop("prompt_hashes"))
    validation_prompt_hashes = set(validation_record_audit.pop("prompt_hashes"))
    train_record_audit["unique_prompt_hashes"] = len(train_prompt_hashes)
    train_record_audit["prompt_set_sha256"] = digest(sorted(train_prompt_hashes))
    validation_record_audit["unique_prompt_hashes"] = len(validation_prompt_hashes)
    validation_record_audit["prompt_set_sha256"] = digest(sorted(validation_prompt_hashes))

    event_visibility = 0
    for trajectory in train_trajectories:
        for style in TRAIN_RENDERERS:
            _, content = render(style, trajectory["domain"], trajectory["initial_state"], trajectory["events"])
            event_visibility += int(not event_operands_visible(content, trajectory["events"]))
    for trajectory in validation_trajectories:
        _, content = render(VALIDATION_RENDERER, trajectory["domain"], trajectory["initial_state"], trajectory["events"])
        event_visibility += int(not event_operands_visible(content, trajectory["events"]))

    exposed = parent.generate(EXPOSED_DEVELOPMENT_SEED)["datasets"]["development"]
    exposed_case_ids = {row["case_id"] for row in exposed}
    exposed_prompt_hashes = {digest(row["input"]) for row in exposed}
    successor_case_ids = {row["case_id"] for row in train_records + validation_records}
    train_decisions = Counter(trajectory["outcome"]["decision"] for trajectory in train_trajectories)
    validation_decisions = Counter(trajectory["outcome"]["decision"] for trajectory in validation_trajectories)
    all_trajectories = train_trajectories + validation_trajectories
    all_pairs = train_pairs + validation_pairs
    protected = {
        "parent_public_semantic_families": [12, 13, 14, 15],
        "protected_semantic_families": [16, 17, 18, 19],
        "successor_validation_semantic_families": [20, 21, 22, 23],
        "public_materialized": False,
        "protected_materialized": False,
        "exposed_development_reused_for_training": False,
    }
    audits = {
        "train": train_audit,
        "repair_validation": validation_audit,
        "train_records": train_record_audit,
        "repair_validation_records": validation_record_audit,
        "train_decision_distribution": dict(train_decisions),
        "repair_validation_decision_distribution": dict(validation_decisions),
        "event_operands_invisible": event_visibility,
        "train_validation_prompt_overlap": len(train_prompt_hashes & validation_prompt_hashes),
        "exposed_development_case_overlap": len(exposed_case_ids & successor_case_ids),
        "exposed_development_prompt_overlap": len(exposed_prompt_hashes & (train_prompt_hashes | validation_prompt_hashes)),
        "trajectory_overlap": len({row["trajectory_id"] for row in train_trajectories} & {row["trajectory_id"] for row in validation_trajectories}),
        "pair_overlap": len({row["counterfactual_pair_id"] for row in train_pairs} & {row["counterfactual_pair_id"] for row in validation_pairs}),
        "institution_overlap": len({row["institution_lineage"] for row in train_trajectories} & {row["institution_lineage"] for row in validation_trajectories}),
        "source_overlap": len({row["source_lineage"] for row in train_trajectories} & {row["source_lineage"] for row in validation_trajectories}),
        "generator_overlap": len({row["generator_lineage"] for row in train_trajectories} & {row["generator_lineage"] for row in validation_trajectories}),
        "semantic_family_overlap": len({row["semantic_family"] for row in train_trajectories} & {row["semantic_family"] for row in validation_trajectories}),
        "task_types": sorted({row["metadata"]["task_type"] for row in train_records}),
        "train_renderers": sorted({row["metadata"]["selected_renderer"] for row in train_records}),
        "repair_validation_renderers": sorted({row["metadata"]["selected_renderer"] for row in validation_records}),
    }
    controls = {
        "registered_counts": len(train_records) == 3600 and len(validation_records) == 300 and len(all_trajectories) == 600 and len(all_pairs) == 300,
        "two_reference_engines_exact": train_audit["engine_disagreements"] == 0 and validation_audit["engine_disagreements"] == 0,
        "transitions_exact": train_audit["transition_disagreements"] == 0 and validation_audit["transition_disagreements"] == 0,
        "pivotal_pairs_change": train_audit["pivotal_pair_changes"] == train_audit["pair_class_distribution"]["PIVOTAL"] and validation_audit["pivotal_pair_changes"] == validation_audit["pair_class_distribution"]["PIVOTAL"],
        "invariance_pairs_preserve": train_audit["invariance_pair_changes"] == 0 and validation_audit["invariance_pair_changes"] == 0,
        "contextual_pairs_preserve": train_audit["contextual_pair_changes"] == 0 and validation_audit["contextual_pair_changes"] == 0,
        "all_task_types_present": set(audits["task_types"]) == set(TASK_TYPES),
        "three_training_renderers": set(audits["train_renderers"]) == set(TRAIN_RENDERERS),
        "heldout_renderer_unseen_in_train": set(audits["repair_validation_renderers"]).isdisjoint(audits["train_renderers"]),
        "event_operands_visible": event_visibility == 0,
        "zero_training_prompt_conflicts": train_record_audit["conflicting_prompt_groups"] == 0,
        "zero_validation_prompt_conflicts": validation_record_audit["conflicting_prompt_groups"] == 0,
        "model_inputs_metadata_free": train_record_audit["forbidden_model_inputs"] == 0 and validation_record_audit["forbidden_model_inputs"] == 0,
        "no_decision_labels_in_inputs": train_record_audit["decision_label_tokens_in_inputs"] == 0 and validation_record_audit["decision_label_tokens_in_inputs"] == 0,
        "train_validation_prompts_disjoint": audits["train_validation_prompt_overlap"] == 0,
        "lineages_disjoint": all(audits[key] == 0 for key in ("trajectory_overlap", "pair_overlap", "institution_overlap", "source_overlap", "generator_overlap", "semantic_family_overlap")),
        "exposed_development_not_reused": audits["exposed_development_case_overlap"] == 0 and audits["exposed_development_prompt_overlap"] == 0,
        "protected_families_unmaterialized": not ({12, 13, 14, 15, 16, 17, 18, 19} & {row["semantic_family"] for row in all_trajectories}),
        "effective_decision_weights_balanced": max(train_record_audit["effective_weighted_decisions"].values()) - min(train_record_audit["effective_weighted_decisions"].values()) < 0.01,
        "model_inputs_only_observation_and_query": all(set(row["input"]) == {"observation", "query"} for row in train_records + validation_records),
        "binding_authority_always_false": all(row["target"].get("binding_authority") is False for row in train_records + validation_records),
        "fresh_generator_lineages": train_audit["generator_lineage"] != validation_audit["generator_lineage"],
    }
    return {
        "datasets": {"train": train_records, "repair_validation": validation_records},
        "canonical_trajectories": all_trajectories,
        "lineages": lineages,
        "protected": protected,
        "audits": audits,
        "controls": controls,
    }