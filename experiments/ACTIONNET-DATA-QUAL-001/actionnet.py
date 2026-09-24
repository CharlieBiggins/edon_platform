#!/usr/bin/env python3
"""Semantic-first bounded ActionNet generator and qualification helpers."""

from __future__ import annotations

import hashlib
import json
import random
import re
from collections import Counter, defaultdict
from copy import deepcopy
from typing import Any


SEMANTIC_STATES = ("TRUE", "FALSE", "UNKNOWN", "MISSING", "CONTESTED", "INVALID")
DECISIONS = ("ALLOW", "DENY", "ABSTAIN", "CONTESTED", "INVALID")
INTERVENTIONS = (
    "REVOKE_AUTHORITY", "EXPIRE_TIME", "EVIDENCE_UNKNOWN", "EVIDENCE_MISSING",
    "ADD_CONFLICT", "MALFORM_INPUT", "EXHAUST_RESOURCE", "POLICY_DENY",
)
FORBIDDEN_INPUT_KEYS = {"expected", "label", "target", "oracle", "reference_decision", "semantic_state", "failed_conditions"}
FORBIDDEN_DECISION_TOKENS = {"ALLOW", "DENY", "ABSTAIN", "CONTESTED", "INVALID"}


def canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode()


def digest(value: Any) -> str:
    return "sha256:" + hashlib.sha256(canonical(value)).hexdigest()


def opaque(prefix: str, *parts: Any) -> str:
    payload = ":".join(str(part) for part in parts).encode()
    return prefix + "-" + hashlib.sha256(payload).hexdigest()[:16]


def family_config(family_id: int) -> dict[str, Any]:
    return {
        "family_id": family_id,
        "required_rank": 2 + family_id % 3,
        "valid_from": 1 + family_id % 2,
        "valid_to": 8 + family_id % 4,
        "base_capacity": 4 + family_id % 3,
        "workflow_required": bool(family_id % 2),
        "authority_mode": ("DIRECT", "DELEGATED")[family_id % 2],
    }


def initial_state(config: dict[str, Any], pair_index: int) -> dict[str, Any]:
    capacity = config["base_capacity"] + pair_index % 3
    return {
        "actor_id": opaque("actor", config["family_id"], pair_index),
        "actor_rank": config["required_rank"] + 1 + pair_index % 2,
        "required_rank": config["required_rank"],
        "delegated": config["authority_mode"] == "DELEGATED",
        "revoked": False,
        "scope_match": True,
        "query_time": config["valid_from"] + 1,
        "valid_from": config["valid_from"],
        "valid_to": config["valid_to"],
        "evidence": "TRUE",
        "capacity": capacity,
        "demand": 1 + pair_index % max(1, capacity - 1),
        "workflow_ready": True,
        "conflict": False,
        "malformed": False,
        "policy_allows": True,
    }


def intervention_event(kind: str, state: dict[str, Any]) -> dict[str, Any]:
    return {
        "REVOKE_AUTHORITY": {"type": "SET_REVOKED", "value": True},
        "EXPIRE_TIME": {"type": "SET_TIME", "value": state["valid_to"] + 1},
        "EVIDENCE_UNKNOWN": {"type": "SET_EVIDENCE", "value": "UNKNOWN"},
        "EVIDENCE_MISSING": {"type": "SET_EVIDENCE", "value": "MISSING"},
        "ADD_CONFLICT": {"type": "SET_CONFLICT", "value": True},
        "MALFORM_INPUT": {"type": "SET_MALFORMED", "value": True},
        "EXHAUST_RESOURCE": {"type": "SET_CAPACITY", "value": 0},
        "POLICY_DENY": {"type": "SET_POLICY", "value": False},
    }[kind]


def neutral_event(kind: str, state: dict[str, Any]) -> dict[str, Any]:
    return {
        "REVOKE_AUTHORITY": {"type": "SET_REVOKED", "value": state["revoked"]},
        "EXPIRE_TIME": {"type": "SET_TIME", "value": state["query_time"]},
        "EVIDENCE_UNKNOWN": {"type": "SET_EVIDENCE", "value": state["evidence"]},
        "EVIDENCE_MISSING": {"type": "SET_EVIDENCE", "value": state["evidence"]},
        "ADD_CONFLICT": {"type": "SET_CONFLICT", "value": state["conflict"]},
        "MALFORM_INPUT": {"type": "SET_MALFORMED", "value": state["malformed"]},
        "EXHAUST_RESOURCE": {"type": "SET_CAPACITY", "value": state["capacity"]},
        "POLICY_DENY": {"type": "SET_POLICY", "value": state["policy_allows"]},
    }[kind]


def transition_a(state: dict[str, Any], event: dict[str, Any]) -> dict[str, Any]:
    result = deepcopy(state)
    kind = event["type"]
    if kind == "NOOP":
        return result
    mapping = {
        "SET_REVOKED": "revoked", "SET_TIME": "query_time", "SET_EVIDENCE": "evidence",
        "SET_CONFLICT": "conflict", "SET_MALFORMED": "malformed",
        "SET_CAPACITY": "capacity", "SET_POLICY": "policy_allows",
    }
    result[mapping[kind]] = event["value"]
    return result


def transition_b(state: dict[str, Any], event: dict[str, Any]) -> dict[str, Any]:
    result = {key: value for key, value in state.items()}
    operations = {
        "NOOP": None,
        "SET_REVOKED": ("revoked", event.get("value")),
        "SET_TIME": ("query_time", event.get("value")),
        "SET_EVIDENCE": ("evidence", event.get("value")),
        "SET_CONFLICT": ("conflict", event.get("value")),
        "SET_MALFORMED": ("malformed", event.get("value")),
        "SET_CAPACITY": ("capacity", event.get("value")),
        "SET_POLICY": ("policy_allows", event.get("value")),
    }
    operation = operations[event["type"]]
    if operation is not None:
        result[operation[0]] = operation[1]
    return result


def evaluate_a(state: dict[str, Any]) -> dict[str, Any]:
    failed: list[str] = []
    if state["malformed"]:
        semantic, decision, failed = "INVALID", "INVALID", ["MALFORMED_INPUT"]
    elif state["conflict"]:
        semantic, decision, failed = "CONTESTED", "CONTESTED", ["AUTHORITY_CONFLICT"]
    elif state["revoked"] or not state["scope_match"] or state["actor_rank"] < state["required_rank"]:
        semantic, decision, failed = "FALSE", "DENY", ["AUTHORITY"]
    elif not state["policy_allows"] or not state["valid_from"] <= state["query_time"] <= state["valid_to"] or state["evidence"] == "FALSE":
        semantic, decision, failed = "FALSE", "DENY", ["POLICY_OR_TIME"]
    elif state["evidence"] in {"UNKNOWN", "MISSING"}:
        semantic, decision, failed = state["evidence"], "ABSTAIN", ["EVIDENCE"]
    elif not state["workflow_ready"] or state["demand"] > state["capacity"]:
        semantic, decision, failed = "UNKNOWN", "ABSTAIN", ["WORKFLOW_OR_RESOURCE"]
    else:
        semantic, decision = "TRUE", "ALLOW"
    return {
        "semantic_state": semantic,
        "decision": decision,
        "authority_path": [state["actor_id"], "registered-authority"],
        "evidence_path": [state["evidence"]],
        "failed_conditions": failed,
        "resource_delta": -state["demand"] if decision == "ALLOW" else 0,
        "workflow_effect": "ADVANCE" if decision == "ALLOW" else "BLOCKED",
    }


def evaluate_b(state: dict[str, Any]) -> dict[str, Any]:
    factors = {
        "malformed": state["malformed"],
        "conflict": state["conflict"],
        "authority": state["revoked"] or not state["scope_match"] or state["actor_rank"] < state["required_rank"],
        "policy_time": (not state["policy_allows"]) or state["query_time"] < state["valid_from"] or state["query_time"] > state["valid_to"] or state["evidence"] == "FALSE",
        "evidence": state["evidence"] in {"UNKNOWN", "MISSING"},
        "execution": (not state["workflow_ready"]) or state["demand"] > state["capacity"],
    }
    if factors["malformed"]:
        semantic, decision, failed = "INVALID", "INVALID", ["MALFORMED_INPUT"]
    elif factors["conflict"]:
        semantic, decision, failed = "CONTESTED", "CONTESTED", ["AUTHORITY_CONFLICT"]
    elif factors["authority"]:
        semantic, decision, failed = "FALSE", "DENY", ["AUTHORITY"]
    elif factors["policy_time"]:
        semantic, decision, failed = "FALSE", "DENY", ["POLICY_OR_TIME"]
    elif factors["evidence"]:
        semantic, decision, failed = state["evidence"], "ABSTAIN", ["EVIDENCE"]
    elif factors["execution"]:
        semantic, decision, failed = "UNKNOWN", "ABSTAIN", ["WORKFLOW_OR_RESOURCE"]
    else:
        semantic, decision, failed = "TRUE", "ALLOW", []
    return {
        "semantic_state": semantic,
        "decision": decision,
        "authority_path": [state["actor_id"], "registered-authority"],
        "evidence_path": [state["evidence"]],
        "failed_conditions": failed,
        "resource_delta": -state["demand"] if decision == "ALLOW" else 0,
        "workflow_effect": "ADVANCE" if decision == "ALLOW" else "BLOCKED",
    }


def execute(initial: dict[str, Any], events: list[dict[str, Any]]) -> tuple[dict[str, Any], dict[str, Any], list[str], int]:
    left, right = deepcopy(initial), deepcopy(initial)
    steps: list[str] = []
    comparisons = 0
    for event in events:
        left = transition_a(left, event)
        right = transition_b(right, event)
        if left != right:
            raise RuntimeError("transition disagreement")
        outcome_a, outcome_b = evaluate_a(left), evaluate_b(right)
        if outcome_a != outcome_b:
            raise RuntimeError("reference outcome disagreement")
        steps.append(outcome_a["semantic_state"])
        comparisons += 1
    return outcome_a, left, steps, comparisons


def public_state(state: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in state.items() if key not in {"malformed"}}


def render(style: str, domain: str, state: dict[str, Any], events: list[dict[str, Any]]) -> tuple[str, str]:
    visible = public_state(state)
    if style == "FORMAL":
        content = json.dumps({"domain": domain, "state": visible, "events": events}, sort_keys=True, separators=(",", ":"))
        return "application/json", content
    if style == "EVENT_LOG":
        event_text = "; ".join(f"{event['type']}={event.get('value', '')}" for event in events)
        content = f"domain={domain}\nactor={visible['actor_id']} rank={visible['actor_rank']} required={visible['required_rank']}\nevidence={visible['evidence']} time={visible['query_time']} window={visible['valid_from']}..{visible['valid_to']}\ncapacity={visible['capacity']} demand={visible['demand']}\nevents={event_text}"
        return "text/plain;profile=event-log", content
    if style == "MEMO":
        event_text = ", then ".join(event["type"].lower().replace("_", " ") for event in events)
        content = f"In the {domain} institution, actor {visible['actor_id']} holds rank {visible['actor_rank']} where rank {visible['required_rank']} is required. Evidence is {visible['evidence'].lower()}, the effective interval is {visible['valid_from']} through {visible['valid_to']}, current time is {visible['query_time']}, and resource demand is {visible['demand']} against capacity {visible['capacity']}. The recorded event sequence is {event_text}. Return a typed institutional certificate."
        return "text/plain;profile=memo", content
    raise ValueError(style)


def input_has_forbidden_fields(value: Any) -> bool:
    if isinstance(value, dict):
        return bool(FORBIDDEN_INPUT_KEYS.intersection(value)) or any(input_has_forbidden_fields(item) for item in value.values())
    if isinstance(value, list):
        return any(input_has_forbidden_fields(item) for item in value)
    return False


def generate(seed: int = 26080850) -> dict[str, Any]:
    rng = random.Random(seed)
    split_plan = {
        "train": {"families": range(0, 8), "institutions": 8, "pairs_per_institution": 30, "domains": ("procurement", "research"), "renderer": "FORMAL", "generator": "generator-train-v1"},
        "development": {"families": range(8, 12), "institutions": 4, "pairs_per_institution": 15, "domains": ("education",), "renderer": "EVENT_LOG", "generator": "generator-development-v1"},
        "public_holdout": {"families": range(12, 16), "institutions": 4, "pairs_per_institution": 15, "domains": ("health",), "renderer": "MEMO", "generator": "generator-public-v1"},
    }
    datasets: dict[str, list[dict[str, Any]]] = defaultdict(list)
    public_labels: list[dict[str, Any]] = []
    canonical_trajectories: list[dict[str, Any]] = []
    lineages: list[dict[str, Any]] = []
    engine_comparisons = 0
    invariance_checks = 0
    pivotal_pair_changes = 0
    invariance_pair_changes = 0
    contextual_pair_changes = 0
    pair_class_counts: Counter[str] = Counter()
    initial_state_mismatches = 0
    nonminimal_pairs = 0
    mechanism_counts: Counter[str] = Counter()
    semantic_counts: Counter[str] = Counter()
    decision_counts: Counter[str] = Counter()
    variant_decisions: dict[str, Counter[str]] = defaultdict(Counter)
    selected_renderers: dict[str, set[str]] = defaultdict(set)
    split_lineages: dict[str, dict[str, set[Any]]] = defaultdict(lambda: defaultdict(set))
    model_input_hashes: set[str] = set()
    exact_duplicates = 0
    forbidden_inputs = 0
    forbidden_identifier_labels = 0
    decision_label_tokens_in_inputs = 0

    renderer_lineages = {style: opaque("renderer", style, "v1") for style in ("FORMAL", "EVENT_LOG", "MEMO")}
    for style, lineage_id in renderer_lineages.items():
        lineages.append({"lineage_id": lineage_id, "lineage_type": "renderer", "version": "1.0.0", "content_sha256": digest({"style": style}), "parents": [], "authority": "EDON Research Lab", "transformation": "render"})

    for split, plan in split_plan.items():
        generator_lineage = opaque("generator", plan["generator"])
        lineages.append({"lineage_id": generator_lineage, "lineage_type": "generator", "version": "1.0.0", "content_sha256": digest({"generator": plan["generator"]}), "parents": [], "authority": "EDON Research Lab", "transformation": "simulate"})
        families = list(plan["families"])
        for institution_index in range(plan["institutions"]):
            family_id = families[institution_index % len(families)]
            config = family_config(family_id)
            domain = plan["domains"][institution_index % len(plan["domains"])]
            institution_lineage = opaque("institution", split, family_id, institution_index, seed)
            source_lineage = opaque("source", split, domain, institution_index, seed)
            lineages.extend([
                {"lineage_id": source_lineage, "lineage_type": "source", "version": "1.0.0", "content_sha256": digest({"synthetic_domain": domain, "family": family_id}), "parents": [], "authority": "EDON Research Lab", "transformation": "original"},
                {"lineage_id": institution_lineage, "lineage_type": "institution", "version": "1.0.0", "content_sha256": digest(config), "parents": [source_lineage], "authority": "EDON Research Lab", "transformation": "compile"},
            ])
            split_lineages[split]["institution"].add(institution_lineage)
            split_lineages[split]["family"].add(family_id)
            split_lineages[split]["generator"].add(generator_lineage)
            split_lineages[split]["domain"].add(domain)
            split_lineages[split]["renderer"].add(plan["renderer"])
            for local_pair in range(plan["pairs_per_institution"]):
                global_pair = institution_index * plan["pairs_per_institution"] + local_pair
                kind = INTERVENTIONS[global_pair % len(INTERVENTIONS)]
                base_state = initial_state(config, global_pair + family_id * 1000)
                pair_id = opaque("pair", split, family_id, institution_index, local_pair, seed)
                pair_mod = global_pair % 6
                pair_class = "PIVOTAL" if pair_mod < 4 else ("INVARIANCE" if pair_mod == 4 else "CONTEXTUAL")
                pair_class_counts[pair_class] += 1
                if pair_class == "CONTEXTUAL":
                    base_state["malformed"] = True
                control_event = neutral_event(kind, base_state)
                changed_event = intervention_event(kind, base_state)
                if pair_class == "INVARIANCE":
                    renamed_state = deepcopy(base_state)
                    renamed_state["actor_id"] = opaque("actor", "pair-invariance", pair_id)
                    variants = (("BASE", base_state, [control_event], None), ("INVARIANT", renamed_state, [control_event], "ACTOR_RENAME"))
                    differing = {key for key in base_state if base_state[key] != renamed_state[key]}
                    nonminimal_pairs += int(differing != {"actor_id"})
                else:
                    variants = (("BASE", base_state, [control_event], None), ("INTERVENTION", base_state, [changed_event], kind))
                    initial_state_mismatches += int(variants[0][1] != variants[1][1])
                    nonminimal_pairs += int(len(variants[0][2]) != 1 or len(variants[1][2]) != 1 or variants[0][2][0]["type"] != variants[1][2][0]["type"])
                pair_decisions: list[str] = []
                for variant, variant_state, events, intervention in variants:
                    outcome, final_state, step_states, comparisons = execute(variant_state, events)
                    engine_comparisons += comparisons
                    pair_decisions.append(outcome["decision"])
                    semantic_counts[outcome["semantic_state"]] += 1
                    decision_counts[outcome["decision"]] += 1
                    variant_decisions["BASE" if variant == "BASE" else "CHANGED"] [outcome["decision"]] += 1
                    if intervention in INTERVENTIONS:
                        mechanism_counts[intervention] += 1

                    renamed = deepcopy(variant_state)
                    renamed["actor_id"] = opaque("actor", "renamed", pair_id)
                    renamed_outcome, _, _, renamed_comparisons = execute(renamed, events)
                    engine_comparisons += renamed_comparisons
                    invariance_checks += 1
                    if {key: value for key, value in renamed_outcome.items() if key != "authority_path"} != {key: value for key, value in outcome.items() if key != "authority_path"}:
                        raise RuntimeError("actor-renaming invariance failure")
                    noop_outcome, _, _, noop_comparisons = execute(variant_state, [{"type": "NOOP"}] + events)
                    engine_comparisons += noop_comparisons
                    invariance_checks += 1
                    if noop_outcome != outcome:
                        raise RuntimeError("no-op invariance failure")

                    trajectory_id = opaque("trajectory", pair_id, variant)
                    renderings = []
                    rendered_content: dict[str, tuple[str, str]] = {}
                    for style in ("FORMAL", "EVENT_LOG", "MEMO"):
                        media_type, content = render(style, domain, variant_state, events)
                        rendered_content[style] = (media_type, content)
                        renderings.append({"renderer_lineage": renderer_lineages[style], "media_type": media_type, "content_sha256": digest(content)})
                    trace_core = {"initial": variant_state, "events": events, "final": final_state, "outcome": outcome}
                    canonical_trajectory = {
                        "trajectory_id": trajectory_id,
                        "institution_lineage": institution_lineage,
                        "generator_lineage": generator_lineage,
                        "initial_state": variant_state,
                        "events": events,
                        "intervention": {"family": intervention} if intervention else None,
                        "final_state": final_state,
                        "reference_decision": outcome["decision"],
                        "paths": {"authority": outcome["authority_path"], "evidence": outcome["evidence_path"], "workflow": [outcome["workflow_effect"]], "resource": [outcome["resource_delta"]]},
                        "consequences": [{"workflow_effect": outcome["workflow_effect"], "resource_delta": outcome["resource_delta"]}],
                        "certificate": {"semantics_version": "actionnet-data-qual.v1", "oracle_agreement": True, "trace_sha256": digest(trace_core)},
                        "renderings": renderings,
                    }
                    canonical_trajectories.append(canonical_trajectory)

                    selected_style = plan["renderer"]
                    selected_renderers[split].add(selected_style)
                    media_type, content = rendered_content[selected_style]
                    case_id = opaque("case", split, pair_id, variant)
                    model_input = {
                        "case_id": case_id,
                        "institution_lineage": institution_lineage,
                        "observation": {"renderer_lineage": renderer_lineages[selected_style], "media_type": media_type, "content": content},
                        "query": "Return a typed institutional certificate for the described state and event sequence.",
                    }
                    target = {
                        "semantic_state": outcome["semantic_state"], "decision": outcome["decision"],
                        "authority_path": outcome["authority_path"], "evidence_path": outcome["evidence_path"],
                        "failed_conditions": outcome["failed_conditions"], "resource_delta": outcome["resource_delta"],
                        "workflow_effect": outcome["workflow_effect"],
                    }
                    record = {"input": model_input, "target": target, "metadata": {"trajectory_id": trajectory_id, "counterfactual_pair_id": pair_id, "pair_class": pair_class, "variant": variant, "intervention_family": intervention, "generator_lineage": generator_lineage, "semantic_family": family_id, "selected_renderer": selected_style, "training_fields": ["input", "target"]}}
                    if split == "public_holdout":
                        datasets[split].append({"input": model_input})
                        public_labels.append({"case_id": case_id, "target": target})
                    else:
                        datasets[split].append(record)
                    input_hash = digest(model_input)
                    if input_hash in model_input_hashes:
                        exact_duplicates += 1
                    model_input_hashes.add(input_hash)
                    split_lineages[split]["prompt"].add(input_hash)
                    forbidden_inputs += int(input_has_forbidden_fields(model_input))
                    forbidden_identifier_labels += int(any(token.lower() in case_id.lower() for token in FORBIDDEN_DECISION_TOKENS))
                    input_tokens = set(re.findall(r"[A-Z]+", content.upper()))
                    decision_label_tokens_in_inputs += int(bool(input_tokens & FORBIDDEN_DECISION_TOKENS))
                changed = int(pair_decisions[0] != pair_decisions[1])
                if pair_class == "PIVOTAL":
                    pivotal_pair_changes += changed
                elif pair_class == "INVARIANCE":
                    invariance_pair_changes += changed
                else:
                    contextual_pair_changes += changed

    split_pairs = {split: len(rows) // 2 for split, rows in datasets.items()}
    protected = {"semantic_families": [16, 17, 18, 19], "domains": ["protected-domain-a", "protected-domain-b"], "seed_materialized": False, "examples": 0}
    audits = {
        "engine_comparisons": engine_comparisons,
        "engine_disagreements": 0,
        "transition_disagreements": 0,
        "invariance_checks": invariance_checks,
        "invariance_failures": 0,
        "counterfactual_pairs": sum(split_pairs.values()),
        "pair_class_distribution": dict(pair_class_counts),
        "pivotal_pair_changes": pivotal_pair_changes,
        "invariance_pair_changes": invariance_pair_changes,
        "contextual_pair_changes": contextual_pair_changes,
        "initial_state_mismatches": initial_state_mismatches,
        "nonminimal_pairs": nonminimal_pairs,
        "exact_duplicate_inputs": exact_duplicates,
        "forbidden_model_inputs": forbidden_inputs,
        "label_encoded_identifiers": forbidden_identifier_labels,
        "decision_label_tokens_in_inputs": decision_label_tokens_in_inputs,
        "semantic_distribution": dict(semantic_counts),
        "decision_distribution": dict(decision_counts),
        "variant_decision_distribution": {variant: dict(counts) for variant, counts in variant_decisions.items()},
        "mechanism_distribution": dict(mechanism_counts),
        "selected_renderers": {split: sorted(values) for split, values in selected_renderers.items()},
    }
    return {"datasets": dict(datasets), "public_labels": public_labels, "canonical_trajectories": canonical_trajectories, "lineages": lineages, "split_lineages": split_lineages, "protected": protected, "audits": audits}


def split_disjoint(split_lineages: dict[str, dict[str, set[Any]]], key: str) -> bool:
    values = [split_lineages[split][key] for split in ("train", "development", "public_holdout")]
    return not (values[0] & values[1] or values[0] & values[2] or values[1] & values[2])