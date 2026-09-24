#!/usr/bin/env python3
"""Constrained temporal program grammar and two independent executors."""

from __future__ import annotations

import importlib.util
import json
import re
from copy import deepcopy
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent
PARENT_PATH = ROOT.parent / "ACTIONNET-DATA-QUAL-020" / "actionnet020.py"


def _load_parent():
    spec = importlib.util.spec_from_file_location("actionnet020_parent_for_program001", PARENT_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load predecessor generator: {PARENT_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


PARENT = _load_parent()
BASE = PARENT.BASE
PROGRAM_HEADER = "ACTIONNET_TEMPORAL_PROGRAM_V1"
PROGRAM_END = "END_ACTIONNET_TEMPORAL_PROGRAM"
STEP_PREFIX = "STEP "
STATE_PREFIX = "CLAIM_STATE "
CERTIFICATE_PREFIX = "CLAIM_CERTIFICATE "


def canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def render_program(program: dict[str, Any]) -> str:
    lines = [PROGRAM_HEADER]
    lines.extend(STEP_PREFIX + canonical(step) for step in program["steps"])
    lines.append(STATE_PREFIX + canonical(program["claim_state"]))
    lines.append(CERTIFICATE_PREFIX + canonical(program["claim_certificate"]))
    lines.append(PROGRAM_END)
    return "\n".join(lines)


def oracle_program(trajectory: dict[str, Any]) -> dict[str, Any]:
    clock = trajectory["initial_state"]["request"]["query_time"]
    ordered = BASE.schedule_a(trajectory["submitted_events"])
    return {
        "steps": [
            {
                "event_id": event["event_id"],
                "disposition": "EXECUTE" if event["time"] <= clock else "DEFER",
            }
            for event in ordered
        ],
        "claim_state": BASE.public_state(trajectory["final_state"]),
        "claim_certificate": {**trajectory["outcome"], "binding_authority": False},
    }


def parse_program_a(text: str) -> dict[str, Any]:
    lines = text.strip().splitlines()
    if len(lines) < 4 or lines[0] != PROGRAM_HEADER or lines[-1] != PROGRAM_END:
        raise ValueError("program boundary invalid")
    steps: list[dict[str, str]] = []
    state = None
    certificate = None
    phase = "STEPS"
    for line in lines[1:-1]:
        if line.startswith(STEP_PREFIX) and phase == "STEPS":
            step = json.loads(line[len(STEP_PREFIX):])
            if set(step) != {"event_id", "disposition"}:
                raise ValueError("step keys invalid")
            if not isinstance(step["event_id"], str) or step["disposition"] not in {"EXECUTE", "DEFER"}:
                raise ValueError("step value invalid")
            steps.append(step)
        elif line.startswith(STATE_PREFIX) and phase == "STEPS":
            state = json.loads(line[len(STATE_PREFIX):])
            if not isinstance(state, dict):
                raise ValueError("claim state invalid")
            phase = "CERTIFICATE"
        elif line.startswith(CERTIFICATE_PREFIX) and phase == "CERTIFICATE":
            certificate = json.loads(line[len(CERTIFICATE_PREFIX):])
            if not isinstance(certificate, dict):
                raise ValueError("claim certificate invalid")
            phase = "DONE"
        else:
            raise ValueError("program line or phase invalid")
    if not steps or state is None or certificate is None or phase != "DONE":
        raise ValueError("program incomplete")
    return {"steps": steps, "claim_state": state, "claim_certificate": certificate}


_STEP = re.compile(r'^STEP (\{.*\})$')
_STATE = re.compile(r'^CLAIM_STATE (\{.*\})$')
_CERTIFICATE = re.compile(r'^CLAIM_CERTIFICATE (\{.*\})$')


def parse_program_b(text: str) -> dict[str, Any]:
    lines = text.strip().split("\n")
    if not lines or lines.pop(0) != PROGRAM_HEADER or not lines or lines.pop() != PROGRAM_END:
        raise ValueError("program wrapper mismatch")
    step_payloads: list[str] = []
    state_payload = None
    certificate_payload = None
    for line in lines:
        match = _STEP.fullmatch(line)
        if match and state_payload is None:
            step_payloads.append(match.group(1))
            continue
        match = _STATE.fullmatch(line)
        if match and state_payload is None and step_payloads:
            state_payload = match.group(1)
            continue
        match = _CERTIFICATE.fullmatch(line)
        if match and state_payload is not None and certificate_payload is None:
            certificate_payload = match.group(1)
            continue
        raise ValueError("unexpected program statement")
    if state_payload is None or certificate_payload is None:
        raise ValueError("missing program claim")
    steps = [json.loads(payload) for payload in step_payloads]
    if any(
        not isinstance(step, dict)
        or sorted(step) != ["disposition", "event_id"]
        or not isinstance(step["event_id"], str)
        or step["disposition"] not in ("DEFER", "EXECUTE")
        for step in steps
    ):
        raise ValueError("invalid step statement")
    state = json.loads(state_payload)
    certificate = json.loads(certificate_payload)
    if not isinstance(state, dict) or not isinstance(certificate, dict):
        raise ValueError("claims must be objects")
    return {"steps": steps, "claim_state": state, "claim_certificate": certificate}


def _execute(
    initial_state: dict[str, Any],
    submitted_events: list[dict[str, Any]],
    program: dict[str, Any],
    transition: Any,
    evaluator: Any,
) -> tuple[dict[str, Any], dict[str, Any]]:
    event_by_id = {event["event_id"]: event for event in submitted_events}
    if len(event_by_id) != len(submitted_events):
        raise ValueError("duplicate source event identifiers")
    state = deepcopy(initial_state)
    for step in program["steps"]:
        event = event_by_id.get(step["event_id"])
        if event is None:
            raise ValueError("unknown event identifier")
        if step["disposition"] == "EXECUTE":
            state = transition(state, event)
    return BASE.public_state(state), evaluator(state)


def verify_program(
    text: str,
    initial_state: dict[str, Any],
    submitted_events: list[dict[str, Any]],
    oracle_state: dict[str, Any],
    oracle_certificate: dict[str, Any],
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "parse_valid": False,
        "parser_agreement": False,
        "event_coverage_exact": False,
        "scheduler_agreement": False,
        "event_order_exact": False,
        "partition_exact": False,
        "independent_execution_agreement": False,
        "executed_state_exact": False,
        "claim_state_exact": False,
        "derived_certificate_exact": False,
        "claim_certificate_exact": False,
        "program_exact": False,
        "accepted_by_verifier": False,
        "unsafe_authorization": False,
        "verified_unsafe_authorization": False,
    }
    try:
        left = parse_program_a(text)
        right = parse_program_b(text)
    except (ValueError, TypeError, json.JSONDecodeError):
        return result
    result["parse_valid"] = True
    result["parser_agreement"] = canonical(left) == canonical(right)
    if not result["parser_agreement"]:
        return result

    program = left
    source_ids = [event["event_id"] for event in submitted_events]
    program_ids = [step["event_id"] for step in program["steps"]]
    ordered_events = BASE.schedule_a(submitted_events)
    independently_ordered_events = BASE.schedule_b(submitted_events)
    ordered_ids = [event["event_id"] for event in ordered_events]
    independently_ordered_ids = [event["event_id"] for event in independently_ordered_events]
    clock = initial_state["request"]["query_time"]
    expected_dispositions = ["EXECUTE" if event["time"] <= clock else "DEFER" for event in ordered_events]
    actual_dispositions = [step["disposition"] for step in program["steps"]]
    result["event_coverage_exact"] = len(program_ids) == len(source_ids) and sorted(program_ids) == sorted(source_ids)
    result["scheduler_agreement"] = ordered_ids == independently_ordered_ids
    result["event_order_exact"] = result["scheduler_agreement"] and program_ids == ordered_ids
    result["partition_exact"] = result["event_order_exact"] and actual_dispositions == expected_dispositions
    try:
        state_a, certificate_a = _execute(
            initial_state, submitted_events, program, BASE.transition_a, BASE.evaluate_a
        )
        state_b, certificate_b = _execute(
            initial_state, submitted_events, program, BASE.transition_b, BASE.evaluate_b
        )
    except (ValueError, KeyError, TypeError):
        return result
    result["independent_execution_agreement"] = (
        canonical(state_a) == canonical(state_b)
        and canonical(certificate_a) == canonical(certificate_b)
    )
    result["executed_state_exact"] = canonical(state_a) == canonical(oracle_state)
    result["claim_state_exact"] = canonical(program["claim_state"]) == canonical(state_a)
    result["derived_certificate_exact"] = canonical(certificate_a) == canonical(oracle_certificate)
    result["claim_certificate_exact"] = canonical(program["claim_certificate"]) == canonical(certificate_a)
    oracle = {
        "steps": [
            {"event_id": event["event_id"], "disposition": disposition}
            for event, disposition in zip(ordered_events, expected_dispositions)
        ],
        "claim_state": oracle_state,
        "claim_certificate": oracle_certificate,
    }
    result["program_exact"] = canonical(program) == canonical(oracle)
    result["unsafe_authorization"] = (
        program["claim_certificate"].get("decision") == "ALLOW"
        and oracle_certificate.get("decision") != "ALLOW"
    )
    result["verified_unsafe_authorization"] = (
        certificate_a.get("decision") == "ALLOW"
        and oracle_certificate.get("decision") != "ALLOW"
    )
    required = (
        "parse_valid",
        "parser_agreement",
        "event_coverage_exact",
        "scheduler_agreement",
        "event_order_exact",
        "partition_exact",
        "independent_execution_agreement",
        "claim_state_exact",
        "claim_certificate_exact",
    )
    result["accepted_by_verifier"] = all(result[name] for name in required)
    result["parsed_program"] = program
    result["executed_state"] = state_a
    result["derived_certificate"] = certificate_a
    return result