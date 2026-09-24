#!/usr/bin/env python3
"""Compile compact model outputs into canonical, hash-bearing DEV-009 records.

The compiler never executes an event or chooses a decision.  It only orders JSON
keys, forces the non-authoritative runtime boundary, derives changed fields from
the model-predicted post-state, and hashes model-predicted states.
"""

from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from typing import Any

from eventnet_io import parse_single_observation


CERTIFICATE_KEYS = {
    "semantic_state", "decision", "authority_path", "evidence_path", "routing_path",
    "failed_conditions", "resource_delta", "workflow_effect", "binding_authority",
}
RAW_TRANSITION_KEYS = {"post_state", "semantic_state", "decision", "failed_conditions", "binding_authority"}
RAW_QUEUE_KEYS = {
    "ordered_event_ids", "executed_event_ids", "deferred_event_ids", "step_semantics",
    "final_state", "binding_authority",
}
RAW_PAIR_KEYS = {
    "decision_changed", "base_certificate", "comparison_certificate",
    "causal_event_change_paths", "changed_post_state_paths", "binding_authority",
}


def canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def digest(value: Any) -> str:
    return "sha256:" + hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()


def changed_fields(before: Any, after: Any, prefix: str = "") -> dict[str, dict[str, Any]]:
    if isinstance(before, dict) and isinstance(after, dict):
        result: dict[str, dict[str, Any]] = {}
        for key in sorted(set(before) | set(after)):
            path = f"{prefix}.{key}" if prefix else key
            if key not in before or key not in after:
                result[path] = {"before": before.get(key), "after": after.get(key)}
            else:
                result.update(changed_fields(before[key], after[key], path))
        return result
    if before != after:
        return {prefix: {"before": before, "after": after}}
    return {}


def valid_raw(task_type: str, value: Any) -> bool:
    if not isinstance(value, dict):
        return False
    keys = set(value)
    if task_type == "CERTIFICATE":
        return keys == CERTIFICATE_KEYS and value.get("binding_authority") is False
    if task_type == "TRANSITION":
        return (
            keys == RAW_TRANSITION_KEYS
            and isinstance(value.get("post_state"), dict)
            and isinstance(value.get("failed_conditions"), list)
            and value.get("binding_authority") is False
        )
    if task_type == "QUEUE_TRACE":
        return (
            keys == RAW_QUEUE_KEYS
            and isinstance(value.get("final_state"), dict)
            and all(isinstance(value.get(key), list) for key in ("ordered_event_ids", "executed_event_ids", "deferred_event_ids", "step_semantics"))
            and value.get("binding_authority") is False
        )
    if task_type == "PAIR_CONTRAST":
        return (
            keys == RAW_PAIR_KEYS
            and isinstance(value.get("decision_changed"), bool)
            and isinstance(value.get("base_certificate"), dict)
            and isinstance(value.get("comparison_certificate"), dict)
            and isinstance(value.get("causal_event_change_paths"), list)
            and isinstance(value.get("changed_post_state_paths"), list)
            and value.get("binding_authority") is False
        )
    return False


def compile_prediction(task_type: str, compiler_input: dict[str, Any], value: Any) -> dict[str, Any]:
    raw = deepcopy(value) if isinstance(value, dict) else {}
    raw["binding_authority"] = False
    if task_type == "CERTIFICATE":
        return raw
    if task_type == "TRANSITION":
        observation = compiler_input["observation"]
        initial_state, _ = parse_single_observation(observation["content"])
        post_state = raw.get("post_state") if isinstance(raw.get("post_state"), dict) else {}
        return {
            "post_state": post_state,
            "changed_fields": changed_fields(initial_state, post_state),
            "semantic_state": raw.get("semantic_state"),
            "decision": raw.get("decision"),
            "failed_conditions": raw.get("failed_conditions") if isinstance(raw.get("failed_conditions"), list) else [],
            "final_state_sha256": digest(post_state),
            "binding_authority": False,
        }
    if task_type == "QUEUE_TRACE":
        final_state = raw.get("final_state") if isinstance(raw.get("final_state"), dict) else {}
        return {
            "ordered_event_ids": raw.get("ordered_event_ids") if isinstance(raw.get("ordered_event_ids"), list) else [],
            "executed_event_ids": raw.get("executed_event_ids") if isinstance(raw.get("executed_event_ids"), list) else [],
            "deferred_event_ids": raw.get("deferred_event_ids") if isinstance(raw.get("deferred_event_ids"), list) else [],
            "step_semantics": raw.get("step_semantics") if isinstance(raw.get("step_semantics"), list) else [],
            "final_state": final_state,
            "final_state_sha256": digest(final_state),
            "binding_authority": False,
        }
    if task_type == "PAIR_CONTRAST":
        return {
            "decision_changed": raw.get("decision_changed"),
            "base_certificate": raw.get("base_certificate") if isinstance(raw.get("base_certificate"), dict) else {},
            "comparison_certificate": raw.get("comparison_certificate") if isinstance(raw.get("comparison_certificate"), dict) else {},
            "causal_event_change_paths": raw.get("causal_event_change_paths") if isinstance(raw.get("causal_event_change_paths"), list) else [],
            "changed_post_state_paths": raw.get("changed_post_state_paths") if isinstance(raw.get("changed_post_state_paths"), list) else [],
            "binding_authority": False,
        }
    raise ValueError(f"unknown task type: {task_type}")