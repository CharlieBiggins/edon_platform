#!/usr/bin/env python3
"""Transparent input-only compact-target ceiling for CEREBRUM-DEV-009."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent
SOURCE = ROOT.parent / "ACTIONNET-DATA-QUAL-009" / "actionnet_multigen.py"
SPEC = importlib.util.spec_from_file_location("actionnet_multigen_repair_rules_source", SOURCE)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("cannot load ActionNet-009 semantics")
actionnet = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(actionnet)


from eventnet_io import parse_single_observation


def execute_observation(content: str) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], list[dict[str, Any]]]:
    state, events = parse_single_observation(content)
    outcome, final_state, _, receipt, _ = actionnet.execute(state, events)
    return outcome, final_state, receipt, events


def predict_input(model_input: dict[str, Any]) -> dict[str, Any]:
    observation = model_input["observation"]
    query = model_input["query"]
    content = observation["content"]
    if observation["media_type"] == "application/json;profile=event-queue-pair-v1":
        pair = json.loads(content)
        base_outcome, base_state, _, base_events = execute_observation(pair["base_observation"])
        comparison_outcome, comparison_state, _, comparison_events = execute_observation(pair["comparison_observation"])
        return {
            "decision_changed": base_outcome["decision"] != comparison_outcome["decision"],
            "base_certificate": base_outcome,
            "comparison_certificate": comparison_outcome,
            "causal_event_change_paths": sorted(actionnet.changed_fields(base_events, comparison_events)),
            "changed_post_state_paths": sorted(actionnet.changed_fields(base_state, comparison_state)),
            "binding_authority": False,
        }
    outcome, final_state, receipt, _ = execute_observation(content)
    if query.startswith("Apply the deterministic event queue"):
        return outcome
    if query.startswith("Apply the queue"):
        return {
            "post_state": actionnet.public_state(final_state),
            "semantic_state": outcome["semantic_state"],
            "decision": outcome["decision"],
            "failed_conditions": outcome["failed_conditions"],
            "binding_authority": False,
        }
    if query.startswith("Return exactly: ordered_event_ids"):
        return {
            "ordered_event_ids": receipt["ordered_event_ids"],
            "executed_event_ids": receipt["executed_event_ids"],
            "deferred_event_ids": receipt["deferred_event_ids"],
            "step_semantics": actionnet.compact_step_semantics(receipt),
            "final_state": actionnet.public_state(final_state),
            "binding_authority": False,
        }
    raise ValueError(f"unknown EventNet task: {query}")