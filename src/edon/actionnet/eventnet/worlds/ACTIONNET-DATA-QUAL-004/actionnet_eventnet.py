#!/usr/bin/env python3
"""Deterministic event-queued, multi-actor ActionNet data generator.

This is an additive successor to ACTIONNET-DATA-QUAL-003.  It is a fresh
implementation: the predecessor is consulted only for historical-overlap audits,
never for state construction, transition semantics, or oracle evaluation.
"""

from __future__ import annotations

import hashlib
import heapq
import importlib.util
import json
import re
from collections import Counter, defaultdict
from copy import deepcopy
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parent
PROTOCOL_ID = "ACTIONNET-DATA-QUAL-004"
RESULT_ID = "ACTIONNET-DATA-QUAL-004-result-v1.0.0"
DATASET_ID = "ACTIONNET-EVENTNET-DATASET-v4.0.0"
TRAIN_SEED = 26081004
VALIDATION_SEED = 26081005
TRAIN_RENDERERS = ("FORMAL", "EVENT_STREAM", "OPERATIONS_MEMO")
VALIDATION_RENDERER = "CASE_DOCKET"
TASK_TYPES = ("CERTIFICATE", "TRANSITION", "QUEUE_TRACE", "PAIR_CONTRAST")
DECISIONS = ("ALLOW", "DENY", "ABSTAIN", "CONTESTED", "INVALID")
SEMANTIC_STATES = ("TRUE", "FALSE", "UNKNOWN", "MISSING", "CONTESTED", "INVALID")
PIVOTAL_MECHANISMS = (
    "REVOCATION_PROPAGATION",
    "DELAYED_EVIDENCE",
    "APPROVAL_WITHDRAWAL",
    "RESOURCE_CONTENTION",
    "POLICY_CHANGE",
    "ROUTING_REJECTION",
    "JURISDICTION_SHIFT",
    "CONFLICT_ASSERTION",
    "MALFORMED_REQUEST",
    "PRIORITY_RACE",
    "EVIDENCE_EXPIRY",
    "UNRESOLVED_APPEAL",
)


def canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def digest(value: Any) -> str:
    payload = value if isinstance(value, bytes) else canonical(value).encode("utf-8")
    return "sha256:" + hashlib.sha256(payload).hexdigest()


def opaque(prefix: str, *parts: Any) -> str:
    payload = ":".join(str(part) for part in parts).encode("utf-8")
    return prefix + "-" + hashlib.sha256(payload).hexdigest()[:16]


def institution_config(family_id: int, domain: str, institution_index: int) -> dict[str, Any]:
    scopes = ("authorize", "procure", "enroll", "credential", "review", "allocate")
    return {
        "family_id": family_id,
        "domain": domain,
        "source_institution": opaque("institution-node", PROTOCOL_ID, family_id, institution_index, "source"),
        "target_institution": opaque("institution-node", PROTOCOL_ID, family_id, institution_index, "target"),
        "required_rank": 2 + family_id % 3,
        "scope": scopes[family_id % len(scopes)],
        "policy_version": 3 + family_id % 5,
        "capacity": 8 + family_id % 4,
        "required_approvals": ("domain_owner", "risk_officer") if family_id % 2 == 0 else ("domain_owner", "records_officer"),
        "cross_institution": institution_index % 2 == 0,
    }


def initial_state(config: dict[str, Any], pair_index: int) -> dict[str, Any]:
    requester = opaque("actor", PROTOCOL_ID, config["family_id"], pair_index, "requester")
    delegator = opaque("actor", PROTOCOL_ID, config["family_id"], pair_index, "delegator")
    approver = opaque("actor", PROTOCOL_ID, config["family_id"], pair_index, "approver")
    reviewer = opaque("actor", PROTOCOL_ID, config["family_id"], pair_index, "reviewer")
    query_time = 10
    demand = 3 + pair_index % 3
    return {
        "request": {
            "request_id": opaque("request", PROTOCOL_ID, config["family_id"], pair_index),
            "scope": config["scope"],
            "query_time": query_time,
            "source_institution": config["source_institution"],
            "target_institution": config["target_institution"] if config["cross_institution"] else config["source_institution"],
            "required_policy_version": config["policy_version"],
            "well_formed": True,
        },
        "actors": {
            "requester": {"actor_id": requester, "rank": config["required_rank"] + 1},
            "delegator": {"actor_id": delegator, "rank": config["required_rank"] + 2},
            "approver": {"actor_id": approver, "rank": config["required_rank"] + 1},
            "reviewer": {"actor_id": reviewer, "rank": config["required_rank"] + 1},
        },
        "authority": {
            "active": True,
            "revoked": False,
            "scope_match": True,
            "required_rank": config["required_rank"],
            "valid_from": 1,
            "valid_to": 20,
        },
        "evidence": {
            "status": "TRUE",
            "source": opaque("evidence-source", PROTOCOL_ID, config["family_id"], pair_index),
            "received_at": 2,
            "valid_until": 20,
        },
        "workflow": {
            "required_approvals": list(config["required_approvals"]),
            "approvals": list(config["required_approvals"]),
            "appeal_open": False,
            "appeal_resolved": True,
        },
        "resources": {"capacity": config["capacity"], "reserved": 1, "demand": demand},
        "routing": {
            "required": config["cross_institution"],
            "accepted": True,
            "jurisdiction_match": True,
        },
        "policy": {"allows": True, "version": config["policy_version"], "effective_at": 1},
        "conflict": False,
    }


def make_event(
    pair_id: str,
    ordinal: int,
    operation: str,
    target: str,
    value: Any,
    *,
    time: int,
    priority: int,
    actor_id: str,
) -> dict[str, Any]:
    return {
        "event_id": opaque("event", PROTOCOL_ID, pair_id, ordinal, operation, target, value, time, priority),
        "time": time,
        "priority": priority,
        "sequence": ordinal,
        "actor_id": actor_id,
        "operation": operation,
        "target": target,
        "value": value,
    }


def common_events(state: dict[str, Any], pair_id: str) -> list[dict[str, Any]]:
    actors = state["actors"]
    return [
        make_event(
            pair_id,
            0,
            "SET_POLICY_VERSION",
            "policy.version",
            state["policy"]["version"],
            time=2,
            priority=30,
            actor_id=actors["reviewer"]["actor_id"],
        ),
        make_event(
            pair_id,
            1,
            "ADD_APPROVAL",
            "workflow.approvals",
            state["workflow"]["required_approvals"][0],
            time=4,
            priority=30,
            actor_id=actors["approver"]["actor_id"],
        ),
        make_event(
            pair_id,
            2,
            "SET_ROUTE_ACCEPTED",
            "routing.accepted",
            True,
            time=5,
            priority=30,
            actor_id=actors["reviewer"]["actor_id"],
        ),
    ]


def pivotal_events(mechanism: str, state: dict[str, Any], pair_id: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    requester = state["actors"]["requester"]["actor_id"]
    delegator = state["actors"]["delegator"]["actor_id"]
    approver = state["actors"]["approver"]["actor_id"]
    reviewer = state["actors"]["reviewer"]["actor_id"]
    base = common_events(state, pair_id)
    changed = deepcopy(base)

    def event(ordinal: int, operation: str, target: str, value: Any, time: int = 7, priority: int = 20, actor: str = reviewer) -> dict[str, Any]:
        return make_event(pair_id, ordinal, operation, target, value, time=time, priority=priority, actor_id=actor)

    if mechanism == "REVOCATION_PROPAGATION":
        base.append(event(3, "SET_DELEGATION_REVOKED", "authority.revoked", False, actor=delegator))
        changed.append(event(3, "SET_DELEGATION_REVOKED", "authority.revoked", True, actor=delegator))
    elif mechanism == "DELAYED_EVIDENCE":
        state["evidence"]["status"] = "MISSING"
        state["evidence"]["received_at"] = None
        base.append(event(3, "SET_EVIDENCE_STATUS", "evidence.status", "TRUE", time=8, actor=reviewer))
        base.append(event(4, "SET_EVIDENCE_RECEIVED_AT", "evidence.received_at", 8, time=8, priority=21, actor=reviewer))
        changed.append(event(3, "SET_EVIDENCE_STATUS", "evidence.status", "TRUE", time=12, actor=reviewer))
        changed.append(event(4, "SET_EVIDENCE_RECEIVED_AT", "evidence.received_at", 12, time=12, priority=21, actor=reviewer))
    elif mechanism == "APPROVAL_WITHDRAWAL":
        approval = state["workflow"]["required_approvals"][-1]
        base.append(event(3, "ADD_APPROVAL", "workflow.approvals", approval, actor=approver))
        changed.append(event(3, "REMOVE_APPROVAL", "workflow.approvals", approval, actor=approver))
    elif mechanism == "RESOURCE_CONTENTION":
        first_delta = state["resources"]["capacity"] // 2
        second_delta = state["resources"]["capacity"] - first_delta
        base.extend([
            event(3, "ADJUST_RESOURCE_RESERVATION", "resources.reserved", 0, time=7, priority=20, actor=requester),
            event(4, "ADJUST_RESOURCE_RESERVATION", "resources.reserved", 0, time=7, priority=20, actor=approver),
        ])
        changed.extend([
            event(3, "ADJUST_RESOURCE_RESERVATION", "resources.reserved", first_delta, time=7, priority=20, actor=requester),
            event(4, "ADJUST_RESOURCE_RESERVATION", "resources.reserved", second_delta, time=7, priority=20, actor=approver),
        ])
    elif mechanism == "POLICY_CHANGE":
        base.append(event(3, "SET_POLICY_ALLOWED", "policy.allows", True))
        changed.append(event(3, "SET_POLICY_ALLOWED", "policy.allows", False))
    elif mechanism == "ROUTING_REJECTION":
        state["routing"]["required"] = True
        base.append(event(3, "SET_ROUTE_ACCEPTED", "routing.accepted", True))
        changed.append(event(3, "SET_ROUTE_ACCEPTED", "routing.accepted", False))
    elif mechanism == "JURISDICTION_SHIFT":
        state["routing"]["required"] = True
        base.append(event(3, "SET_JURISDICTION_MATCH", "routing.jurisdiction_match", True))
        changed.append(event(3, "SET_JURISDICTION_MATCH", "routing.jurisdiction_match", False))
    elif mechanism == "CONFLICT_ASSERTION":
        base.append(event(3, "SET_CONFLICT", "conflict", False))
        changed.append(event(3, "SET_CONFLICT", "conflict", True))
    elif mechanism == "MALFORMED_REQUEST":
        base.append(event(3, "SET_REQUEST_WELL_FORMED", "request.well_formed", True, actor=requester))
        changed.append(event(3, "SET_REQUEST_WELL_FORMED", "request.well_formed", False, actor=requester))
    elif mechanism == "PRIORITY_RACE":
        base.extend([
            event(3, "SET_DELEGATION_REVOKED", "authority.revoked", True, time=7, priority=10, actor=delegator),
            event(4, "SET_DELEGATION_REVOKED", "authority.revoked", False, time=7, priority=20, actor=delegator),
        ])
        changed.extend([
            event(3, "SET_DELEGATION_REVOKED", "authority.revoked", True, time=7, priority=10, actor=delegator),
            event(4, "SET_DELEGATION_REVOKED", "authority.revoked", False, time=7, priority=5, actor=delegator),
        ])
    elif mechanism == "EVIDENCE_EXPIRY":
        base.append(event(3, "SET_EVIDENCE_VALID_UNTIL", "evidence.valid_until", 20))
        changed.append(event(3, "SET_EVIDENCE_VALID_UNTIL", "evidence.valid_until", 9))
    elif mechanism == "UNRESOLVED_APPEAL":
        base.extend([
            event(3, "OPEN_APPEAL", "workflow.appeal_open", True, time=7, actor=requester),
            event(4, "RESOLVE_APPEAL", "workflow.appeal_open", False, time=9, actor=reviewer),
        ])
        changed.extend([
            event(3, "OPEN_APPEAL", "workflow.appeal_open", True, time=7, actor=requester),
            event(4, "RESOLVE_APPEAL", "workflow.appeal_open", False, time=12, actor=reviewer),
        ])
    else:
        raise ValueError(mechanism)
    # Deliberately provide nonchronological input to require scheduler semantics.
    return list(reversed(base)), list(reversed(changed))


def invariance_variants(state: dict[str, Any], pair_id: str) -> tuple[dict[str, Any], list[dict[str, Any]], dict[str, Any], list[dict[str, Any]]]:
    base_events = common_events(state, pair_id) + [
        make_event(
            pair_id,
            3,
            "SET_AUTHORITY_SCOPE_MATCH",
            "authority.scope_match",
            True,
            time=7,
            priority=20,
            actor_id=state["actors"]["delegator"]["actor_id"],
        )
    ]
    renamed = deepcopy(state)
    renamed["actors"]["requester"]["actor_id"] = opaque("actor", PROTOCOL_ID, "invariance-rename", pair_id)
    return state, list(reversed(base_events)), renamed, base_events


def contextual_variants(state: dict[str, Any], pair_id: str) -> tuple[dict[str, Any], list[dict[str, Any]], dict[str, Any], list[dict[str, Any]]]:
    state["request"]["well_formed"] = False
    base_events = common_events(state, pair_id) + [
        make_event(pair_id, 3, "ADJUST_RESOURCE_RESERVATION", "resources.reserved", 0, time=7, priority=20, actor_id=state["actors"]["requester"]["actor_id"])
    ]
    comparison_events = common_events(state, pair_id) + [
        make_event(pair_id, 3, "ADJUST_RESOURCE_RESERVATION", "resources.reserved", 5, time=7, priority=20, actor_id=state["actors"]["requester"]["actor_id"])
    ]
    return state, list(reversed(base_events)), deepcopy(state), list(reversed(comparison_events))


def set_path(state: dict[str, Any], path: str, value: Any) -> None:
    parts = path.split(".")
    target: dict[str, Any] = state
    for part in parts[:-1]:
        target = target[part]
    target[parts[-1]] = value


def transition_a(state: dict[str, Any], event: dict[str, Any]) -> dict[str, Any]:
    result = deepcopy(state)
    operation = event["operation"]
    value = event["value"]
    if operation in {
        "SET_POLICY_VERSION",
        "SET_ROUTE_ACCEPTED",
        "SET_DELEGATION_REVOKED",
        "SET_EVIDENCE_STATUS",
        "SET_EVIDENCE_RECEIVED_AT",
        "SET_POLICY_ALLOWED",
        "SET_JURISDICTION_MATCH",
        "SET_CONFLICT",
        "SET_REQUEST_WELL_FORMED",
        "SET_EVIDENCE_VALID_UNTIL",
        "SET_AUTHORITY_SCOPE_MATCH",
    }:
        set_path(result, event["target"], value)
    elif operation == "ADD_APPROVAL":
        if value not in result["workflow"]["approvals"]:
            result["workflow"]["approvals"].append(value)
        result["workflow"]["approvals"].sort()
    elif operation == "REMOVE_APPROVAL":
        result["workflow"]["approvals"] = [item for item in result["workflow"]["approvals"] if item != value]
    elif operation == "ADJUST_RESOURCE_RESERVATION":
        result["resources"]["reserved"] = max(0, result["resources"]["reserved"] + int(value))
    elif operation == "OPEN_APPEAL":
        result["workflow"]["appeal_open"] = True
        result["workflow"]["appeal_resolved"] = False
    elif operation == "RESOLVE_APPEAL":
        result["workflow"]["appeal_open"] = False
        result["workflow"]["appeal_resolved"] = True
    elif operation != "NOOP":
        raise ValueError(operation)
    return result


def transition_b(state: dict[str, Any], event: dict[str, Any]) -> dict[str, Any]:
    result = json.loads(canonical(state))
    operation = event["operation"]
    direct_paths = {
        "SET_POLICY_VERSION": ("policy", "version"),
        "SET_ROUTE_ACCEPTED": ("routing", "accepted"),
        "SET_DELEGATION_REVOKED": ("authority", "revoked"),
        "SET_EVIDENCE_STATUS": ("evidence", "status"),
        "SET_EVIDENCE_RECEIVED_AT": ("evidence", "received_at"),
        "SET_POLICY_ALLOWED": ("policy", "allows"),
        "SET_JURISDICTION_MATCH": ("routing", "jurisdiction_match"),
        "SET_CONFLICT": (None, "conflict"),
        "SET_REQUEST_WELL_FORMED": ("request", "well_formed"),
        "SET_EVIDENCE_VALID_UNTIL": ("evidence", "valid_until"),
        "SET_AUTHORITY_SCOPE_MATCH": ("authority", "scope_match"),
    }
    if operation in direct_paths:
        parent, key = direct_paths[operation]
        if parent is None:
            result[key] = event["value"]
        else:
            result[parent][key] = event["value"]
    elif operation in {"ADD_APPROVAL", "REMOVE_APPROVAL"}:
        approvals = set(result["workflow"]["approvals"])
        if operation == "ADD_APPROVAL":
            approvals.add(event["value"])
        else:
            approvals.discard(event["value"])
        result["workflow"]["approvals"] = sorted(approvals)
    elif operation == "ADJUST_RESOURCE_RESERVATION":
        result["resources"]["reserved"] = max(0, int(result["resources"]["reserved"]) + int(event["value"]))
    elif operation in {"OPEN_APPEAL", "RESOLVE_APPEAL"}:
        resolved = operation == "RESOLVE_APPEAL"
        result["workflow"]["appeal_open"] = not resolved
        result["workflow"]["appeal_resolved"] = resolved
    elif operation != "NOOP":
        raise ValueError(operation)
    return result


def evaluate_a(state: dict[str, Any]) -> dict[str, Any]:
    query_time = state["request"]["query_time"]
    requester_rank = state["actors"]["requester"]["rank"]
    authority = state["authority"]
    evidence = state["evidence"]
    workflow = state["workflow"]
    resources = state["resources"]
    routing = state["routing"]
    policy = state["policy"]
    if not state["request"]["well_formed"]:
        semantic, decision, failed = "INVALID", "INVALID", ["MALFORMED_REQUEST"]
    elif state["conflict"] or (workflow["appeal_open"] and not workflow["appeal_resolved"]):
        semantic, decision, failed = "CONTESTED", "CONTESTED", ["UNRESOLVED_CONTEST"]
    elif not authority["active"] or authority["revoked"] or not authority["scope_match"] or requester_rank < authority["required_rank"] or not authority["valid_from"] <= query_time <= authority["valid_to"]:
        semantic, decision, failed = "FALSE", "DENY", ["AUTHORITY"]
    elif routing["required"] and (not routing["accepted"] or not routing["jurisdiction_match"]):
        semantic, decision, failed = "FALSE", "DENY", ["ROUTING_OR_JURISDICTION"]
    elif not policy["allows"] or policy["version"] != state["request"]["required_policy_version"] or query_time < policy["effective_at"]:
        semantic, decision, failed = "FALSE", "DENY", ["POLICY"]
    elif evidence["status"] == "FALSE" or (evidence["valid_until"] is not None and evidence["valid_until"] < query_time):
        semantic, decision, failed = "FALSE", "DENY", ["EVIDENCE_FALSE_OR_EXPIRED"]
    elif evidence["status"] in {"UNKNOWN", "MISSING"} or evidence["received_at"] is None or evidence["received_at"] > query_time:
        semantic = evidence["status"] if evidence["status"] in {"UNKNOWN", "MISSING"} else "UNKNOWN"
        decision, failed = "ABSTAIN", ["EVIDENCE_UNAVAILABLE"]
    elif not set(workflow["required_approvals"]).issubset(workflow["approvals"]):
        semantic, decision, failed = "UNKNOWN", "ABSTAIN", ["WORKFLOW_APPROVAL"]
    elif resources["demand"] > resources["capacity"] - resources["reserved"]:
        semantic, decision, failed = "UNKNOWN", "ABSTAIN", ["RESOURCE_CAPACITY"]
    else:
        semantic, decision, failed = "TRUE", "ALLOW", []
    return {
        "semantic_state": semantic,
        "decision": decision,
        "authority_path": [state["actors"]["requester"]["actor_id"], state["actors"]["delegator"]["actor_id"], state["request"]["target_institution"]],
        "evidence_path": [state["evidence"]["source"], state["evidence"]["status"]],
        "routing_path": [state["request"]["source_institution"], state["request"]["target_institution"]],
        "failed_conditions": failed,
        "resource_delta": -resources["demand"] if decision == "ALLOW" else 0,
        "workflow_effect": "ADVANCE" if decision == "ALLOW" else "BLOCKED",
        "binding_authority": False,
    }


def evaluate_b(state: dict[str, Any]) -> dict[str, Any]:
    now = state["request"]["query_time"]
    missing_approval = bool(set(state["workflow"]["required_approvals"]) - set(state["workflow"]["approvals"]))
    factors = {
        "invalid": not state["request"]["well_formed"],
        "contested": state["conflict"] or state["workflow"]["appeal_open"] and not state["workflow"]["appeal_resolved"],
        "authority": (
            not state["authority"]["active"]
            or state["authority"]["revoked"]
            or not state["authority"]["scope_match"]
            or state["actors"]["requester"]["rank"] < state["authority"]["required_rank"]
            or now < state["authority"]["valid_from"]
            or now > state["authority"]["valid_to"]
        ),
        "routing": state["routing"]["required"] and (not state["routing"]["accepted"] or not state["routing"]["jurisdiction_match"]),
        "policy": not state["policy"]["allows"] or state["policy"]["version"] != state["request"]["required_policy_version"] or now < state["policy"]["effective_at"],
        "evidence_false": state["evidence"]["status"] == "FALSE" or (state["evidence"]["valid_until"] is not None and state["evidence"]["valid_until"] < now),
        "evidence_unavailable": state["evidence"]["status"] in {"UNKNOWN", "MISSING"} or state["evidence"]["received_at"] is None or state["evidence"]["received_at"] > now,
        "workflow": missing_approval,
        "resource": state["resources"]["demand"] > state["resources"]["capacity"] - state["resources"]["reserved"],
    }
    ordered = (
        ("invalid", "INVALID", "INVALID", ["MALFORMED_REQUEST"]),
        ("contested", "CONTESTED", "CONTESTED", ["UNRESOLVED_CONTEST"]),
        ("authority", "FALSE", "DENY", ["AUTHORITY"]),
        ("routing", "FALSE", "DENY", ["ROUTING_OR_JURISDICTION"]),
        ("policy", "FALSE", "DENY", ["POLICY"]),
        ("evidence_false", "FALSE", "DENY", ["EVIDENCE_FALSE_OR_EXPIRED"]),
        ("evidence_unavailable", state["evidence"]["status"] if state["evidence"]["status"] in {"UNKNOWN", "MISSING"} else "UNKNOWN", "ABSTAIN", ["EVIDENCE_UNAVAILABLE"]),
        ("workflow", "UNKNOWN", "ABSTAIN", ["WORKFLOW_APPROVAL"]),
        ("resource", "UNKNOWN", "ABSTAIN", ["RESOURCE_CAPACITY"]),
    )
    semantic, decision, failed = "TRUE", "ALLOW", []
    for name, candidate_semantic, candidate_decision, candidate_failed in ordered:
        if factors[name]:
            semantic, decision, failed = candidate_semantic, candidate_decision, candidate_failed
            break
    demand = state["resources"]["demand"]
    return {
        "semantic_state": semantic,
        "decision": decision,
        "authority_path": [state["actors"]["requester"]["actor_id"], state["actors"]["delegator"]["actor_id"], state["request"]["target_institution"]],
        "evidence_path": [state["evidence"]["source"], state["evidence"]["status"]],
        "routing_path": [state["request"]["source_institution"], state["request"]["target_institution"]],
        "failed_conditions": failed,
        "resource_delta": -demand if decision == "ALLOW" else 0,
        "workflow_effect": "ADVANCE" if decision == "ALLOW" else "BLOCKED",
        "binding_authority": False,
    }


def schedule_a(events: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(events, key=lambda item: (item["time"], item["priority"], item["sequence"], item["event_id"]))


def schedule_b(events: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    heap: list[tuple[int, int, int, str, dict[str, Any]]] = []
    for item in events:
        heapq.heappush(heap, (item["time"], item["priority"], item["sequence"], item["event_id"], item))
    ordered: list[dict[str, Any]] = []
    while heap:
        ordered.append(heapq.heappop(heap)[-1])
    return ordered


def _run_engine(
    initial: dict[str, Any],
    events: list[dict[str, Any]],
    scheduler: Any,
    transition: Any,
    evaluator: Any,
) -> tuple[dict[str, Any], dict[str, Any], list[dict[str, Any]], dict[str, Any]]:
    state = deepcopy(initial)
    query_time = initial["request"]["query_time"]
    ordered = scheduler(events)
    executed: list[str] = []
    deferred: list[str] = []
    steps: list[dict[str, Any]] = []
    for event in ordered:
        if event["time"] > query_time:
            deferred.append(event["event_id"])
            continue
        state = transition(state, event)
        outcome = evaluator(state)
        executed.append(event["event_id"])
        steps.append({
            "event_id": event["event_id"],
            "operation": event["operation"],
            "semantic_state": outcome["semantic_state"],
            "decision": outcome["decision"],
            "state_sha256": digest(state),
        })
    outcome = evaluator(state)
    receipt = {
        "ordered_event_ids": [event["event_id"] for event in ordered],
        "executed_event_ids": executed,
        "deferred_event_ids": deferred,
        "step_semantics": steps,
        "final_state_sha256": digest(state),
    }
    return outcome, state, steps, receipt


def execute(initial: dict[str, Any], events: list[dict[str, Any]]) -> tuple[dict[str, Any], dict[str, Any], list[dict[str, Any]], dict[str, Any], int]:
    left = _run_engine(initial, events, schedule_a, transition_a, evaluate_a)
    right = _run_engine(initial, events, schedule_b, transition_b, evaluate_b)
    if left != right:
        raise RuntimeError("independent scheduler/transition/oracle disagreement")
    return (*left, len(left[2]) + 1)


def compact_commutative_events(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Combine only adjacent, same-key resource deltas after canonical scheduling."""
    ordered = schedule_a(events)
    compacted: list[dict[str, Any]] = []
    index = 0
    while index < len(ordered):
        event = ordered[index]
        if event["operation"] != "ADJUST_RESOURCE_RESERVATION":
            compacted.append(event)
            index += 1
            continue
        group = [event]
        cursor = index + 1
        while cursor < len(ordered):
            candidate = ordered[cursor]
            if (
                candidate["operation"] == event["operation"]
                and candidate["target"] == event["target"]
                and candidate["time"] == event["time"]
                and candidate["priority"] == event["priority"]
            ):
                group.append(candidate)
                cursor += 1
            else:
                break
        if len(group) == 1:
            compacted.append(event)
        else:
            merged = deepcopy(event)
            merged["event_id"] = opaque("event-batch", *(item["event_id"] for item in group))
            merged["value"] = sum(int(item["value"]) for item in group)
            compacted.append(merged)
        index = cursor
    return compacted


def public_state(state: dict[str, Any]) -> dict[str, Any]:
    return deepcopy(state)


def event_text(event: dict[str, Any]) -> str:
    return (
        f"id={event['event_id']} time={event['time']} priority={event['priority']} sequence={event['sequence']} "
        f"actor={event['actor_id']} operation={event['operation']} target={event['target']} value={canonical(event['value'])}"
    )


def render(style: str, domain: str, state: dict[str, Any], events: list[dict[str, Any]]) -> tuple[str, str]:
    visible = public_state(state)
    if style == "FORMAL":
        return "application/json;profile=actionnet-eventnet-v4", canonical({"domain": domain, "institutional_state": visible, "event_queue": events})
    if style == "EVENT_STREAM":
        lines = [f"DOMAIN={domain}", "STATE=" + canonical(visible), "EVENT_QUEUE_BEGIN"]
        lines.extend(event_text(event) for event in events)
        lines.append("EVENT_QUEUE_END")
        return "text/plain;profile=event-stream-v4", "\n".join(lines)
    if style == "OPERATIONS_MEMO":
        queue = " ".join(f"EVENT[{event_text(event)}]" for event in events)
        content = (
            f"Operations memorandum for domain {domain}. The typed institutional state is {canonical(visible)}. "
            f"The submitted queue is intentionally not guaranteed to be chronological. Apply events by time, priority, sequence, and identifier. {queue}"
        )
        return "text/plain;profile=operations-memo-v4", content
    if style == "CASE_DOCKET":
        queue = " || ".join(event_text(event) for event in events)
        content = f"DOCKET<{domain}>\nINITIAL_RECORD::{canonical(visible)}\nSCHEDULED_ENTRIES::{queue}\nDISPOSITION_TIME::{state['request']['query_time']}"
        return "text/plain;profile=case-docket-v1", content
    raise ValueError(style)


def event_operands_visible(content: str, events: list[dict[str, Any]]) -> bool:
    return all(
        canonical(event["value"]) in content
        and str(event["time"]) in content
        and str(event["priority"]) in content
        and event["operation"] in content
        for event in events
    )


def changed_fields(before: Any, after: Any, prefix: str = "") -> dict[str, dict[str, Any]]:
    if isinstance(before, dict) and isinstance(after, dict):
        changes: dict[str, dict[str, Any]] = {}
        for key in sorted(set(before) | set(after)):
            path = f"{prefix}.{key}" if prefix else key
            if key not in before or key not in after:
                changes[path] = {"before": before.get(key), "after": after.get(key)}
            else:
                changes.update(changed_fields(before[key], after[key], path))
        return changes
    if before != after:
        return {prefix: {"before": before, "after": after}}
    return {}


def renderer_lineages() -> tuple[dict[str, str], list[dict[str, Any]]]:
    styles = (*TRAIN_RENDERERS, VALIDATION_RENDERER)
    mapping = {style: opaque("renderer", PROTOCOL_ID, style, "v1") for style in styles}
    records = [
        {
            "lineage_id": lineage,
            "lineage_type": "renderer",
            "version": "1.0.0",
            "content_sha256": digest({"style": style, "schema": "actionnet-event-render-v4"}),
            "parents": [],
            "authority": "EDON Research Lab",
            "transformation": "render-eventnet-v4",
        }
        for style, lineage in mapping.items()
    ]
    records.extend([
        {
            "lineage_id": opaque("scheduler", PROTOCOL_ID, "sorted-reference"),
            "lineage_type": "reference_engine",
            "version": "1.0.0",
            "content_sha256": digest("schedule_a-transition_a-evaluate_a"),
            "parents": [],
            "authority": "EDON Research Lab",
            "transformation": "deterministic-event-execution",
        },
        {
            "lineage_id": opaque("scheduler", PROTOCOL_ID, "heap-reference"),
            "lineage_type": "reference_engine",
            "version": "1.0.0",
            "content_sha256": digest("schedule_b-transition_b-evaluate_b"),
            "parents": [],
            "authority": "EDON Research Lab",
            "transformation": "independent-deterministic-event-execution",
        },
    ])
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
    generator_lineage = opaque("generator", PROTOCOL_ID, split, seed)
    lineages.append({
        "lineage_id": generator_lineage,
        "lineage_type": "generator",
        "version": "1.0.0",
        "content_sha256": digest({"protocol": PROTOCOL_ID, "split": split, "seed": seed, "implementation": "eventnet-independent-v1"}),
        "parents": ["ACTIONNET-DATA-QUAL-003-result-v1.0.0"],
        "authority": "EDON Research Lab",
        "transformation": "fresh-eventnet-generation",
    })
    pair_counts: Counter[str] = Counter()
    mechanism_counts: Counter[str] = Counter()
    decision_counts: Counter[str] = Counter()
    pivotal_counter = 0
    pivotal_changes = invariance_changes = contextual_changes = 0
    engine_comparisons = aggregation_checks = aggregation_failures = 0
    simultaneous_queues = deferred_queues = multi_actor = cross_institution = 0
    for institution_index, family_id in enumerate(families):
        domain = domains[institution_index % len(domains)]
        config = institution_config(family_id, domain, institution_index)
        source_lineage = opaque("source", PROTOCOL_ID, split, seed, domain, institution_index)
        institution_lineage = opaque("institution", PROTOCOL_ID, split, seed, family_id, institution_index)
        authority_graph_lineage = opaque("authority-graph", PROTOCOL_ID, split, seed, family_id, institution_index)
        workflow_graph_lineage = opaque("workflow-graph", PROTOCOL_ID, split, seed, family_id, institution_index)
        lineages.extend([
            {
                "lineage_id": source_lineage,
                "lineage_type": "source",
                "version": "1.0.0",
                "content_sha256": digest({"domain": domain, "family": family_id, "seed": seed}),
                "parents": [],
                "authority": "EDON Research Lab",
                "transformation": "project-authored-synthetic-source-v4",
            },
            {
                "lineage_id": institution_lineage,
                "lineage_type": "institution",
                "version": "1.0.0",
                "content_sha256": digest(config),
                "parents": [source_lineage],
                "authority": "EDON Research Lab",
                "transformation": "compile-institution-v4",
            },
            {
                "lineage_id": authority_graph_lineage,
                "lineage_type": "authority_graph",
                "version": "1.0.0",
                "content_sha256": digest({"family": family_id, "edges": ["requester->delegator", "delegator->institution"]}),
                "parents": [institution_lineage],
                "authority": "EDON Research Lab",
                "transformation": "compile-authority-graph-v1",
            },
            {
                "lineage_id": workflow_graph_lineage,
                "lineage_type": "workflow_graph",
                "version": "1.0.0",
                "content_sha256": digest({"family": family_id, "approvals": config["required_approvals"]}),
                "parents": [institution_lineage],
                "authority": "EDON Research Lab",
                "transformation": "compile-workflow-graph-v1",
            },
        ])
        for local_pair in range(pairs_per_institution):
            global_pair = institution_index * pairs_per_institution + local_pair
            pair_mod = global_pair % 6
            pair_class = "PIVOTAL" if pair_mod < 4 else ("INVARIANCE" if pair_mod == 4 else "CONTEXTUAL")
            pair_counts[pair_class] += 1
            pair_id = opaque("pair", PROTOCOL_ID, split, seed, family_id, institution_index, local_pair)
            state = initial_state(config, global_pair + family_id * 1000)
            if pair_class == "PIVOTAL":
                mechanism = PIVOTAL_MECHANISMS[pivotal_counter % len(PIVOTAL_MECHANISMS)]
                pivotal_counter += 1
                base_events, comparison_events = pivotal_events(mechanism, state, pair_id)
                variants = (("BASE", deepcopy(state), base_events, None), ("INTERVENTION", deepcopy(state), comparison_events, mechanism))
            elif pair_class == "INVARIANCE":
                mechanism = "QUEUE_ORDER_AND_ACTOR_RENAME"
                base_state, base_events, comparison_state, comparison_events = invariance_variants(state, pair_id)
                variants = (("BASE", base_state, base_events, None), ("INVARIANT", comparison_state, comparison_events, mechanism))
            else:
                mechanism = "DECISIVE_CONTEXT_PRESERVATION"
                base_state, base_events, comparison_state, comparison_events = contextual_variants(state, pair_id)
                variants = (("BASE", base_state, base_events, None), ("CONTEXT", comparison_state, comparison_events, mechanism))
            mechanism_counts[mechanism] += 1
            pair_trajectories: list[dict[str, Any]] = []
            for variant, variant_state, events, intervention_family in variants:
                outcome, final_state, step_trace, receipt, comparisons = execute(variant_state, events)
                engine_comparisons += comparisons
                decision_counts[outcome["decision"]] += 1
                simultaneous_queues += int(len({(event["time"], event["priority"]) for event in events}) < len(events))
                deferred_queues += int(bool(receipt["deferred_event_ids"]))
                multi_actor += int(len({actor["actor_id"] for actor in variant_state["actors"].values()}) >= 4)
                cross_institution += int(variant_state["request"]["source_institution"] != variant_state["request"]["target_institution"])

                compacted = compact_commutative_events(events)
                if len(compacted) < len(events):
                    aggregation_checks += 1
                    compact_outcome, compact_state, _, _, _ = execute(variant_state, compacted)
                    if compact_outcome != outcome or compact_state != final_state:
                        aggregation_failures += 1

                trajectory_id = opaque("trajectory", PROTOCOL_ID, pair_id, variant)
                trajectory = {
                    "trajectory_id": trajectory_id,
                    "counterfactual_pair_id": pair_id,
                    "split": split,
                    "domain": domain,
                    "semantic_family": family_id,
                    "institution_lineage": institution_lineage,
                    "source_lineage": source_lineage,
                    "authority_graph_lineage": authority_graph_lineage,
                    "workflow_graph_lineage": workflow_graph_lineage,
                    "generator_lineage": generator_lineage,
                    "pair_class": pair_class,
                    "variant": variant,
                    "intervention_family": intervention_family,
                    "initial_state": variant_state,
                    "submitted_events": events,
                    "execution_receipt": receipt,
                    "step_trace": step_trace,
                    "final_state": final_state,
                    "outcome": outcome,
                    "changed_fields": changed_fields(variant_state, final_state),
                    "trace_sha256": digest({"initial": variant_state, "events": events, "receipt": receipt, "final": final_state, "outcome": outcome}),
                }
                trajectories.append(trajectory)
                pair_trajectories.append(trajectory)
            decision_changed = pair_trajectories[0]["outcome"]["decision"] != pair_trajectories[1]["outcome"]["decision"]
            if pair_class == "PIVOTAL":
                pivotal_changes += int(decision_changed)
            elif pair_class == "INVARIANCE":
                invariance_changes += int(decision_changed)
            else:
                contextual_changes += int(decision_changed)
            pairs.append({
                "counterfactual_pair_id": pair_id,
                "split": split,
                "pair_class": pair_class,
                "intervention_family": mechanism,
                "base": pair_trajectories[0],
                "comparison": pair_trajectories[1],
            })
    audit = {
        "engine_comparisons": engine_comparisons,
        "engine_disagreements": 0,
        "scheduler_disagreements": 0,
        "transition_disagreements": 0,
        "pair_class_distribution": dict(pair_counts),
        "mechanism_distribution": dict(mechanism_counts),
        "decision_distribution": dict(decision_counts),
        "pivotal_pair_changes": pivotal_changes,
        "invariance_pair_changes": invariance_changes,
        "contextual_pair_changes": contextual_changes,
        "aggregation_equivalence_checks": aggregation_checks,
        "aggregation_equivalence_failures": aggregation_failures,
        "simultaneous_event_trajectories": simultaneous_queues,
        "deferred_event_trajectories": deferred_queues,
        "multi_actor_trajectories": multi_actor,
        "cross_institution_trajectories": cross_institution,
        "families": sorted(families),
        "generator_lineage": generator_lineage,
        "aggregate_outcome_sha256": digest(dict(sorted(decision_counts.items()))),
    }
    return trajectories, pairs, lineages, audit


def observation(style: str, renderer_ids: dict[str, str], trajectory: dict[str, Any]) -> dict[str, Any]:
    media_type, content = render(style, trajectory["domain"], trajectory["initial_state"], trajectory["submitted_events"])
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
        "authority_graph_lineage": trajectory["authority_graph_lineage"],
        "workflow_graph_lineage": trajectory["workflow_graph_lineage"],
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
    *,
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
            tasks = (
                (
                    "CERTIFICATE",
                    "Apply the deterministic event queue through the disposition time and return one canonical non-authoritative institutional certificate.",
                    trajectory["outcome"],
                ),
                (
                    "TRANSITION",
                    "Apply the event queue and return the typed post-state, changed fields, final semantics, decision, failed conditions, and execution receipt.",
                    {
                        "post_state": public_state(trajectory["final_state"]),
                        "changed_fields": trajectory["changed_fields"],
                        "semantic_state": trajectory["outcome"]["semantic_state"],
                        "decision": trajectory["outcome"]["decision"],
                        "failed_conditions": trajectory["outcome"]["failed_conditions"],
                        "execution_receipt": trajectory["execution_receipt"],
                        "binding_authority": False,
                    },
                ),
                (
                    "QUEUE_TRACE",
                    "Return the canonical queue order, executed and deferred events, step semantics, and final state hash.",
                    {**trajectory["execution_receipt"], "binding_authority": False},
                ),
            )
            for task_type, query, target in tasks:
                records.append({
                    "case_id": opaque("case", PROTOCOL_ID, trajectory["trajectory_id"], style, task_type),
                    "input": {"observation": obs, "query": query},
                    "target": target,
                    "metadata": metadata(trajectory, style, task_type, weight),
                })
    for pair in pairs:
        base_trajectory = pair["base"]
        comparison = pair["comparison"]
        pair_weight = 2.0 if weighted and pair["pair_class"] == "PIVOTAL" else 1.0
        for style in styles:
            base_obs = observation(style, renderer_ids, base_trajectory)
            comparison_obs = observation(style, renderer_ids, comparison)
            records.append({
                "case_id": opaque("case", PROTOCOL_ID, pair["counterfactual_pair_id"], style, "PAIR_CONTRAST"),
                "input": {
                    "observation": {
                        "renderer_lineage": renderer_ids[style],
                        "media_type": "application/json;profile=event-queue-pair-v1",
                        "content": canonical({"base_observation": base_obs["content"], "comparison_observation": comparison_obs["content"]}),
                    },
                    "query": "Execute both queues and return whether the disposition changes, both certificates, causal event differences, and post-state differences.",
                },
                "target": {
                    "decision_changed": base_trajectory["outcome"]["decision"] != comparison["outcome"]["decision"],
                    "base_certificate": base_trajectory["outcome"],
                    "comparison_certificate": comparison["outcome"],
                    "causal_event_changes": changed_fields(base_trajectory["submitted_events"], comparison["submitted_events"]),
                    "changed_post_state_fields": changed_fields(base_trajectory["final_state"], comparison["final_state"]),
                    "binding_authority": False,
                },
                "metadata": {
                    **metadata(base_trajectory, style, "PAIR_CONTRAST", pair_weight),
                    "trajectory_id": None,
                    "variant": "PAIR",
                    "intervention_family": pair["intervention_family"],
                    "decision": comparison["outcome"]["decision"],
                },
            })
    return records


def input_forbidden(value: Any) -> bool:
    forbidden = {
        "expected",
        "label",
        "target",
        "oracle",
        "reference_decision",
        "semantic_state",
        "failed_conditions",
        "pair_class",
        "variant",
        "intervention_family",
        "trajectory_id",
        "counterfactual_pair_id",
    }
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
    forbidden_inputs = decision_tokens = 0
    for record in records:
        prompt_hash = digest(record["input"])
        conflicts[prompt_hash].add(digest(record["target"]))
        task = record["metadata"]["task_type"]
        task_counts[task] += 1
        renderer_counts[record["metadata"]["selected_renderer"]] += 1
        if task != "PAIR_CONTRAST":
            weighted_decisions[record["metadata"]["decision"]] += record["metadata"]["sample_weight"]
        forbidden_inputs += int(input_forbidden(record["input"]))
        tokens = set(re.findall(r"[A-Z]+", canonical(record["input"]).upper()))
        decision_tokens += int(bool(tokens & set(DECISIONS)))
    return {
        "conflicting_prompt_groups": sum(len(values) > 1 for values in conflicts.values()),
        "task_counts": dict(task_counts),
        "renderer_counts": dict(renderer_counts),
        "effective_weighted_decisions": {key: round(value, 4) for key, value in sorted(weighted_decisions.items())},
        "forbidden_model_inputs": forbidden_inputs,
        "decision_label_tokens_in_inputs": decision_tokens,
        "prompt_hashes": sorted(conflicts),
    }


def historical_overlap(case_ids: set[str], prompt_hashes: set[str]) -> dict[str, int]:
    predecessor = ROOT.parent / "ACTIONNET-DATA-QUAL-003" / "actionnet_multiview.py"
    spec = importlib.util.spec_from_file_location("actionnet_data_qual_003_history", predecessor)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load predecessor for historical-overlap audit")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    previous = module.generate()
    previous_rows = previous["datasets"]["train"] + previous["datasets"]["repair_validation"]
    previous_case_ids = {row["case_id"] for row in previous_rows}
    previous_prompt_hashes = {digest(row["input"]) for row in previous_rows}
    return {
        "predecessor_case_overlap": len(case_ids & previous_case_ids),
        "predecessor_prompt_overlap": len(prompt_hashes & previous_prompt_hashes),
    }


def generate() -> dict[str, Any]:
    renderer_ids, lineages = renderer_lineages()
    train_trajectories, train_pairs, train_lineages, train_audit = generate_split(
        "train", TRAIN_SEED, tuple(range(30, 42)), 20, ("procurement", "research", "education")
    )
    validation_trajectories, validation_pairs, validation_lineages, validation_audit = generate_split(
        "repair_validation", VALIDATION_SEED, tuple(range(50, 54)), 15, ("health-administration", "civic-administration")
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

    all_trajectories = train_trajectories + validation_trajectories
    all_pairs = train_pairs + validation_pairs
    all_records = train_records + validation_records
    event_visibility = 0
    minimum_queue_length = min(len(trajectory["submitted_events"]) for trajectory in all_trajectories)
    for trajectory in train_trajectories:
        for style in TRAIN_RENDERERS:
            _, content = render(style, trajectory["domain"], trajectory["initial_state"], trajectory["submitted_events"])
            event_visibility += int(not event_operands_visible(content, trajectory["submitted_events"]))
    for trajectory in validation_trajectories:
        _, content = render(VALIDATION_RENDERER, trajectory["domain"], trajectory["initial_state"], trajectory["submitted_events"])
        event_visibility += int(not event_operands_visible(content, trajectory["submitted_events"]))

    case_ids = {row["case_id"] for row in all_records}
    historical = historical_overlap(case_ids, train_prompt_hashes | validation_prompt_hashes)
    protected = {
        "predecessor_validation_semantic_families": [20, 21, 22, 23],
        "eventnet_train_semantic_families": list(range(30, 42)),
        "eventnet_repair_validation_semantic_families": list(range(50, 54)),
        "future_public_semantic_families": [54, 55, 56, 57],
        "protected_semantic_families": [58, 59, 60, 61],
        "public_materialized": False,
        "protected_materialized": False,
        "real_institution_materialized": False,
    }
    audits = {
        "train": train_audit,
        "repair_validation": validation_audit,
        "train_records": train_record_audit,
        "repair_validation_records": validation_record_audit,
        "event_operands_invisible": event_visibility,
        "minimum_submitted_queue_length": minimum_queue_length,
        "train_validation_prompt_overlap": len(train_prompt_hashes & validation_prompt_hashes),
        "trajectory_overlap": len({item["trajectory_id"] for item in train_trajectories} & {item["trajectory_id"] for item in validation_trajectories}),
        "pair_overlap": len({item["counterfactual_pair_id"] for item in train_pairs} & {item["counterfactual_pair_id"] for item in validation_pairs}),
        "institution_overlap": len({item["institution_lineage"] for item in train_trajectories} & {item["institution_lineage"] for item in validation_trajectories}),
        "source_overlap": len({item["source_lineage"] for item in train_trajectories} & {item["source_lineage"] for item in validation_trajectories}),
        "generator_overlap": len({item["generator_lineage"] for item in train_trajectories} & {item["generator_lineage"] for item in validation_trajectories}),
        "semantic_family_overlap": len({item["semantic_family"] for item in train_trajectories} & {item["semantic_family"] for item in validation_trajectories}),
        "authority_graph_overlap": len({item["authority_graph_lineage"] for item in train_trajectories} & {item["authority_graph_lineage"] for item in validation_trajectories}),
        "workflow_graph_overlap": len({item["workflow_graph_lineage"] for item in train_trajectories} & {item["workflow_graph_lineage"] for item in validation_trajectories}),
        "task_types": sorted({row["metadata"]["task_type"] for row in train_records}),
        "train_renderers": sorted({row["metadata"]["selected_renderer"] for row in train_records}),
        "repair_validation_renderers": sorted({row["metadata"]["selected_renderer"] for row in validation_records}),
        **historical,
    }
    expected_train_pairs = 12 * 20
    expected_validation_pairs = 4 * 15
    expected_train_records = expected_train_pairs * (2 * 3 + 1) * len(TRAIN_RENDERERS)
    expected_validation_records = expected_validation_pairs * (2 * 3 + 1)
    controls = {
        "registered_counts": len(train_records) == expected_train_records and len(validation_records) == expected_validation_records and len(all_trajectories) == 600 and len(all_pairs) == 300,
        "independent_reference_engines_exact": train_audit["engine_disagreements"] == 0 and validation_audit["engine_disagreements"] == 0,
        "independent_schedulers_exact": train_audit["scheduler_disagreements"] == 0 and validation_audit["scheduler_disagreements"] == 0,
        "transitions_exact": train_audit["transition_disagreements"] == 0 and validation_audit["transition_disagreements"] == 0,
        "pivotal_pairs_change": train_audit["pivotal_pair_changes"] == train_audit["pair_class_distribution"]["PIVOTAL"] and validation_audit["pivotal_pair_changes"] == validation_audit["pair_class_distribution"]["PIVOTAL"],
        "invariance_pairs_preserve": train_audit["invariance_pair_changes"] == 0 and validation_audit["invariance_pair_changes"] == 0,
        "contextual_pairs_preserve": train_audit["contextual_pair_changes"] == 0 and validation_audit["contextual_pair_changes"] == 0,
        "all_pivotal_mechanisms_covered": set(PIVOTAL_MECHANISMS).issubset(train_audit["mechanism_distribution"]) and set(PIVOTAL_MECHANISMS).issubset(validation_audit["mechanism_distribution"]),
        "multi_step_queues": minimum_queue_length >= 4,
        "simultaneous_events_present": train_audit["simultaneous_event_trajectories"] > 0 and validation_audit["simultaneous_event_trajectories"] > 0,
        "deferred_events_present": train_audit["deferred_event_trajectories"] > 0 and validation_audit["deferred_event_trajectories"] > 0,
        "multi_actor_trajectories": train_audit["multi_actor_trajectories"] == len(train_trajectories) and validation_audit["multi_actor_trajectories"] == len(validation_trajectories),
        "cross_institution_coverage": train_audit["cross_institution_trajectories"] > 0 and validation_audit["cross_institution_trajectories"] > 0,
        "safe_aggregation_equivalence": train_audit["aggregation_equivalence_checks"] > 0 and validation_audit["aggregation_equivalence_checks"] > 0 and train_audit["aggregation_equivalence_failures"] == 0 and validation_audit["aggregation_equivalence_failures"] == 0,
        "all_task_types_present": set(audits["task_types"]) == set(TASK_TYPES),
        "three_training_renderers": set(audits["train_renderers"]) == set(TRAIN_RENDERERS),
        "heldout_renderer_unseen_in_train": set(audits["repair_validation_renderers"]).isdisjoint(audits["train_renderers"]),
        "event_operands_visible": event_visibility == 0,
        "zero_training_prompt_conflicts": train_record_audit["conflicting_prompt_groups"] == 0,
        "zero_validation_prompt_conflicts": validation_record_audit["conflicting_prompt_groups"] == 0,
        "model_inputs_metadata_free": train_record_audit["forbidden_model_inputs"] == 0 and validation_record_audit["forbidden_model_inputs"] == 0,
        "no_decision_labels_in_inputs": train_record_audit["decision_label_tokens_in_inputs"] == 0 and validation_record_audit["decision_label_tokens_in_inputs"] == 0,
        "train_validation_prompts_disjoint": audits["train_validation_prompt_overlap"] == 0,
        "lineages_disjoint": all(audits[key] == 0 for key in ("trajectory_overlap", "pair_overlap", "institution_overlap", "source_overlap", "generator_overlap", "semantic_family_overlap", "authority_graph_overlap", "workflow_graph_overlap")),
        "predecessor_not_reused": audits["predecessor_case_overlap"] == 0 and audits["predecessor_prompt_overlap"] == 0,
        "effective_decision_weights_balanced": max(train_record_audit["effective_weighted_decisions"].values()) - min(train_record_audit["effective_weighted_decisions"].values()) < 0.01,
        "model_inputs_only_observation_and_query": all(set(row["input"]) == {"observation", "query"} for row in all_records),
        "binding_authority_always_false": all(row["target"].get("binding_authority") is False for row in all_records),
        "future_public_and_protected_unmaterialized": not ({54, 55, 56, 57, 58, 59, 60, 61} & {item["semantic_family"] for item in all_trajectories}),
        "fresh_generator_lineages": train_audit["generator_lineage"] != validation_audit["generator_lineage"],
    }
    return {
        "datasets": {"train": train_records, "repair_validation": validation_records},
        "canonical_trajectories": all_trajectories,
        "counterfactual_pairs": all_pairs,
        "lineages": lineages,
        "protected": protected,
        "audits": audits,
        "controls": controls,
    }