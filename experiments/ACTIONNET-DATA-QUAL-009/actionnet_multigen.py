#!/usr/bin/env python3
"""Fresh-lineage multi-generator execution repair for CEREBRUM-DEV-009.

The v7 corpus responds to the aggregate CEREBRUM-TRANSFER-006 failure without
reusing any exposed transfer case.  It makes decision-clock deferral,
canonical queue ordering, exact state mutation, and counterfactual state diffs
structural properties of the training distribution.  Two independent engines
must agree on every target before a record is admitted.
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
PROTOCOL_ID = "ACTIONNET-DATA-QUAL-009"
RESULT_ID = "ACTIONNET-DATA-QUAL-009-result-v1.0.0"
DATASET_ID = "ACTIONNET-EXECUTION-TRANSFER-REPAIR-DATASET-v9.0.0"
LEDGER_SEED = 26082409
MATRIX_SEED = 26082410
VALIDATION_SEED = 26082411
TRAIN_RENDERERS_LEDGER = ("CHRONOLOGY_LEDGER", "AUTHORIZATION_WORKPAD")
TRAIN_RENDERERS_MATRIX = ("QUEUE_MATRIX", "STATE_TRANSITION_CARD")
TRAIN_RENDERERS = (*TRAIN_RENDERERS_LEDGER, *TRAIN_RENDERERS_MATRIX)
VALIDATION_RENDERER = "DEPENDENCY_GRAPH_PACKET"
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
    "REVOCATION_RESOURCE_COMPOSITION",
    "POLICY_APPROVAL_COMPOSITION",
    "EVIDENCE_RESOURCE_COMPOSITION",
    "JURISDICTION_CONFLICT_COMPOSITION",
)
FOCUSED_PIVOTAL_SCHEDULE = PIVOTAL_MECHANISMS + (
    "DELAYED_EVIDENCE",
    "PRIORITY_RACE",
    "EVIDENCE_EXPIRY",
    "RESOURCE_CONTENTION",
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
    # The clock varies so a model must compare event time with the stated
    # disposition time instead of memorizing a global cutoff.
    query_time = 8 + pair_index % 5
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
    query_time = state["request"]["query_time"]
    return [
        make_event(
            pair_id,
            0,
            "SET_POLICY_VERSION",
            "policy.version",
            state["policy"]["version"],
            time=query_time - 6,
            priority=30,
            actor_id=actors["reviewer"]["actor_id"],
        ),
        make_event(
            pair_id,
            1,
            "ADD_APPROVAL",
            "workflow.approvals",
            state["workflow"]["required_approvals"][0],
            time=query_time - 4,
            priority=30,
            actor_id=actors["approver"]["actor_id"],
        ),
        make_event(
            pair_id,
            2,
            "SET_ROUTE_ACCEPTED",
            "routing.accepted",
            True,
            time=query_time - 4,
            priority=30,
            actor_id=actors["reviewer"]["actor_id"],
        ),
        make_event(
            pair_id,
            3,
            "SET_EVIDENCE_RECEIVED_AT",
            "evidence.received_at",
            query_time - 5,
            time=query_time - 3,
            priority=20,
            actor_id=actors["reviewer"]["actor_id"],
        ),
        make_event(
            pair_id,
            4,
            "ADJUST_RESOURCE_RESERVATION",
            "resources.reserved",
            1,
            time=query_time - 2,
            priority=20,
            actor_id=actors["requester"]["actor_id"],
        ),
    ]


def decision_clock_events(state: dict[str, Any], pair_id: str) -> list[dict[str, Any]]:
    """Return one to three consequential events that must all be deferred."""
    actors = state["actors"]
    query_time = state["request"]["query_time"]
    count = 1 + int(hashlib.sha256(pair_id.encode("utf-8")).hexdigest()[:2], 16) % 3
    candidates = [
        make_event(
            pair_id, 90, "SET_POLICY_ALLOWED", "policy.allows", False,
            time=query_time + 1, priority=5, actor_id=actors["reviewer"]["actor_id"],
        ),
        make_event(
            pair_id, 91, "SET_CONFLICT", "conflict", True,
            time=query_time + 2, priority=5, actor_id=actors["requester"]["actor_id"],
        ),
        make_event(
            pair_id, 92, "REMOVE_APPROVAL", "workflow.approvals",
            state["workflow"]["required_approvals"][-1],
            time=query_time + 3, priority=5, actor_id=actors["approver"]["actor_id"],
        ),
    ]
    return candidates[:count]


def pivotal_events(mechanism: str, state: dict[str, Any], pair_id: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    requester = state["actors"]["requester"]["actor_id"]
    delegator = state["actors"]["delegator"]["actor_id"]
    approver = state["actors"]["approver"]["actor_id"]
    reviewer = state["actors"]["reviewer"]["actor_id"]
    query_time = state["request"]["query_time"]
    base = common_events(state, pair_id)
    changed = deepcopy(base)

    def event(ordinal: int, operation: str, target: str, value: Any, time: int | None = None, priority: int = 20, actor: str = reviewer) -> dict[str, Any]:
        time = query_time - 1 if time is None else time
        return make_event(pair_id, ordinal, operation, target, value, time=time, priority=priority, actor_id=actor)

    if mechanism == "REVOCATION_PROPAGATION":
        base.append(event(10, "SET_DELEGATION_REVOKED", "authority.revoked", False, actor=delegator))
        changed.append(event(10, "SET_DELEGATION_REVOKED", "authority.revoked", True, actor=delegator))
    elif mechanism == "DELAYED_EVIDENCE":
        state["evidence"]["status"] = "MISSING"
        state["evidence"]["received_at"] = None
        base.append(event(10, "SET_EVIDENCE_STATUS", "evidence.status", "TRUE", time=query_time - 1, actor=reviewer))
        base.append(event(11, "SET_EVIDENCE_RECEIVED_AT", "evidence.received_at", query_time - 1, time=query_time - 1, priority=21, actor=reviewer))
        changed.append(event(10, "SET_EVIDENCE_STATUS", "evidence.status", "TRUE", time=query_time + 1, actor=reviewer))
        changed.append(event(11, "SET_EVIDENCE_RECEIVED_AT", "evidence.received_at", query_time + 1, time=query_time + 1, priority=21, actor=reviewer))
    elif mechanism == "APPROVAL_WITHDRAWAL":
        approval = state["workflow"]["required_approvals"][-1]
        base.append(event(10, "ADD_APPROVAL", "workflow.approvals", approval, actor=approver))
        changed.append(event(10, "REMOVE_APPROVAL", "workflow.approvals", approval, actor=approver))
    elif mechanism == "RESOURCE_CONTENTION":
        first_delta = state["resources"]["capacity"] // 2
        second_delta = state["resources"]["capacity"] - first_delta
        base.extend([
            event(10, "ADJUST_RESOURCE_RESERVATION", "resources.reserved", 0, priority=20, actor=requester),
            event(11, "ADJUST_RESOURCE_RESERVATION", "resources.reserved", 0, priority=20, actor=approver),
        ])
        changed.extend([
            event(10, "ADJUST_RESOURCE_RESERVATION", "resources.reserved", first_delta, priority=20, actor=requester),
            event(11, "ADJUST_RESOURCE_RESERVATION", "resources.reserved", second_delta, priority=20, actor=approver),
        ])
    elif mechanism == "POLICY_CHANGE":
        base.append(event(10, "SET_POLICY_ALLOWED", "policy.allows", True))
        changed.append(event(10, "SET_POLICY_ALLOWED", "policy.allows", False))
    elif mechanism == "ROUTING_REJECTION":
        state["routing"]["required"] = True
        base.append(event(10, "SET_ROUTE_ACCEPTED", "routing.accepted", True))
        changed.append(event(10, "SET_ROUTE_ACCEPTED", "routing.accepted", False))
    elif mechanism == "JURISDICTION_SHIFT":
        state["routing"]["required"] = True
        base.append(event(10, "SET_JURISDICTION_MATCH", "routing.jurisdiction_match", True))
        changed.append(event(10, "SET_JURISDICTION_MATCH", "routing.jurisdiction_match", False))
    elif mechanism == "CONFLICT_ASSERTION":
        base.append(event(10, "SET_CONFLICT", "conflict", False))
        changed.append(event(10, "SET_CONFLICT", "conflict", True))
    elif mechanism == "MALFORMED_REQUEST":
        base.append(event(10, "SET_REQUEST_WELL_FORMED", "request.well_formed", True, actor=requester))
        changed.append(event(10, "SET_REQUEST_WELL_FORMED", "request.well_formed", False, actor=requester))
    elif mechanism == "PRIORITY_RACE":
        base.extend([
            event(10, "SET_DELEGATION_REVOKED", "authority.revoked", True, priority=10, actor=delegator),
            event(11, "SET_DELEGATION_REVOKED", "authority.revoked", False, priority=20, actor=delegator),
        ])
        changed.extend([
            event(10, "SET_DELEGATION_REVOKED", "authority.revoked", True, priority=10, actor=delegator),
            event(11, "SET_DELEGATION_REVOKED", "authority.revoked", False, priority=5, actor=delegator),
        ])
    elif mechanism == "EVIDENCE_EXPIRY":
        base.append(event(10, "SET_EVIDENCE_VALID_UNTIL", "evidence.valid_until", query_time + 4))
        changed.append(event(10, "SET_EVIDENCE_VALID_UNTIL", "evidence.valid_until", query_time - 1))
    elif mechanism == "UNRESOLVED_APPEAL":
        timing_profile = int(hashlib.sha256(pair_id.encode("utf-8")).hexdigest()[:2], 16) % 3
        open_time = query_time - (4, 3, 2)[timing_profile]
        resolved_time = query_time - 1
        unresolved_time = query_time + (1, 2, 3)[timing_profile]
        base.extend([
            event(10, "OPEN_APPEAL", "workflow.appeal_open", True, time=open_time, actor=requester),
            event(11, "RESOLVE_APPEAL", "workflow.appeal_open", False, time=resolved_time, actor=reviewer),
        ])
        changed.extend([
            event(10, "OPEN_APPEAL", "workflow.appeal_open", True, time=open_time, actor=requester),
            event(11, "RESOLVE_APPEAL", "workflow.appeal_open", False, time=unresolved_time, actor=reviewer),
        ])
    elif mechanism == "REVOCATION_RESOURCE_COMPOSITION":
        base.extend([
            event(10, "SET_DELEGATION_REVOKED", "authority.revoked", False, actor=delegator),
            event(11, "ADJUST_RESOURCE_RESERVATION", "resources.reserved", 0, priority=21, actor=requester),
        ])
        changed.extend([
            event(10, "SET_DELEGATION_REVOKED", "authority.revoked", True, actor=delegator),
            event(11, "ADJUST_RESOURCE_RESERVATION", "resources.reserved", state["resources"]["capacity"], priority=21, actor=requester),
        ])
    elif mechanism == "POLICY_APPROVAL_COMPOSITION":
        approval = state["workflow"]["required_approvals"][-1]
        base.extend([
            event(10, "SET_POLICY_ALLOWED", "policy.allows", True, actor=reviewer),
            event(11, "ADD_APPROVAL", "workflow.approvals", approval, priority=21, actor=approver),
        ])
        changed.extend([
            event(10, "SET_POLICY_ALLOWED", "policy.allows", False, actor=reviewer),
            event(11, "REMOVE_APPROVAL", "workflow.approvals", approval, priority=21, actor=approver),
        ])
    elif mechanism == "EVIDENCE_RESOURCE_COMPOSITION":
        base.extend([
            event(10, "SET_EVIDENCE_VALID_UNTIL", "evidence.valid_until", query_time + 4, actor=reviewer),
            event(11, "ADJUST_RESOURCE_RESERVATION", "resources.reserved", 0, priority=21, actor=requester),
        ])
        changed.extend([
            event(10, "SET_EVIDENCE_VALID_UNTIL", "evidence.valid_until", query_time - 1, actor=reviewer),
            event(11, "ADJUST_RESOURCE_RESERVATION", "resources.reserved", state["resources"]["capacity"], priority=21, actor=requester),
        ])
    elif mechanism == "JURISDICTION_CONFLICT_COMPOSITION":
        state["routing"]["required"] = True
        base.extend([
            event(10, "SET_JURISDICTION_MATCH", "routing.jurisdiction_match", True, actor=reviewer),
            event(11, "SET_CONFLICT", "conflict", False, priority=21, actor=requester),
        ])
        changed.extend([
            event(10, "SET_JURISDICTION_MATCH", "routing.jurisdiction_match", False, actor=reviewer),
            event(11, "SET_CONFLICT", "conflict", True, priority=21, actor=requester),
        ])
    else:
        raise ValueError(mechanism)
    future = decision_clock_events(state, pair_id)
    # Deliberately provide nonchronological input to require scheduler semantics.
    return list(reversed(base + future)), list(reversed(changed + future))


def invariance_variants(state: dict[str, Any], pair_id: str) -> tuple[dict[str, Any], list[dict[str, Any]], dict[str, Any], list[dict[str, Any]]]:
    base_events = common_events(state, pair_id) + [
        make_event(
            pair_id,
            10,
            "SET_AUTHORITY_SCOPE_MATCH",
            "authority.scope_match",
            True,
            time=state["request"]["query_time"] - 1,
            priority=20,
            actor_id=state["actors"]["delegator"]["actor_id"],
        )
    ]
    renamed = deepcopy(state)
    renamed["actors"]["requester"]["actor_id"] = opaque("actor", PROTOCOL_ID, "invariance-rename", pair_id)
    future = decision_clock_events(state, pair_id)
    return state, list(reversed(base_events + future)), renamed, (base_events[2:] + future + base_events[:2])


def contextual_variants(state: dict[str, Any], pair_id: str) -> tuple[dict[str, Any], list[dict[str, Any]], dict[str, Any], list[dict[str, Any]]]:
    state["request"]["well_formed"] = False
    base_events = common_events(state, pair_id) + [
        make_event(pair_id, 10, "ADJUST_RESOURCE_RESERVATION", "resources.reserved", 0, time=state["request"]["query_time"] - 1, priority=20, actor_id=state["actors"]["requester"]["actor_id"])
    ]
    comparison_events = common_events(state, pair_id) + [
        make_event(pair_id, 10, "ADJUST_RESOURCE_RESERVATION", "resources.reserved", 5, time=state["request"]["query_time"] - 1, priority=20, actor_id=state["actors"]["requester"]["actor_id"])
    ]
    future = decision_clock_events(state, pair_id)
    return state, list(reversed(base_events + future)), deepcopy(state), list(reversed(comparison_events + future))


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
    if style == "CHRONOLOGY_LEDGER":
        queue = "\n".join(f"LEDGER_ENTRY::{event_text(event)}" for event in events)
        return "text/plain;profile=chronology-ledger-v1", (
            f"CHRONOLOGY_LEDGER domain={domain}\nDECISION_CLOCK={state['request']['query_time']}\n"
            f"INITIAL_STATE={canonical(visible)}\nUNSORTED_ENTRIES_BEGIN\n{queue}\nUNSORTED_ENTRIES_END\n"
            "ORDER=time,priority,sequence,event_id; execute through the clock and defer later entries."
        )
    if style == "AUTHORIZATION_WORKPAD":
        queue = " || ".join(event_text(event) for event in events)
        return "text/plain;profile=authorization-workpad-v1", (
            f"AUTHORIZATION_WORKPAD<{domain}> CLOCK::{state['request']['query_time']} STATE::{canonical(visible)} "
            f"SUBMISSIONS::{queue} RULE::SORT_THEN_EXECUTE_THROUGH_CLOCK_AND_DEFER_LATER"
        )
    if style == "QUEUE_MATRIX":
        return "application/json;profile=queue-matrix-v1", canonical({
            "domain": domain, "decision_clock": state["request"]["query_time"],
            "typed_initial_state": visible, "unsorted_event_matrix": events,
            "canonical_order": ["time", "priority", "sequence", "event_id"], "after_clock": "DEFER",
        })
    if style == "STATE_TRANSITION_CARD":
        queue = "\n".join(f"CARD_EVENT[{event_text(event)}]" for event in events)
        return "text/plain;profile=state-transition-card-v1", (
            f"STATE TRANSITION CARD — {domain}\nClock: {state['request']['query_time']}\n"
            f"Typed start: {canonical(visible)}\nSubmitted events:\n{queue}\n"
            "Apply canonical ascending order only through the clock; retain the rest as deferred."
        )
    if style == "DEPENDENCY_GRAPH_PACKET":
        queue = " ".join(f"GRAPH_EVENT[{event_text(event)}]" for event in events)
        return "text/plain;profile=dependency-graph-packet-v1", (
            f"DEPENDENCY_GRAPH_PACKET domain={domain}. CLOCK={state['request']['query_time']}. "
            f"ROOT_STATE={canonical(visible)}. Submitted graph events are not ordered. Traverse by "
            f"time, priority, sequence, and event identifier through the clock; defer later nodes. {queue}"
        )
    if style == "DECISION_CLOCK_GRID":
        queue = "\n".join(f"GRID_ROW::{event_text(event)}" for event in events)
        return (
            "text/plain;profile=decision-clock-grid-v1",
            f"DECISION_CLOCK_GRID domain={domain}\nINITIAL={canonical(visible)}\nROWS_BEGIN\n{queue}\nROWS_END\n"
            f"EXECUTE_WHEN=time<=DECISION_CLOCK\nDECISION_CLOCK={state['request']['query_time']}",
        )
    if style == "MULTI_SYSTEM_JOURNAL":
        queue = " || ".join(event_text(event) for event in events)
        return (
            "text/plain;profile=multi-system-journal-v1",
            f"MULTI_SYSTEM_JOURNAL<{domain}> STATE::{canonical(visible)} SUBMISSIONS::{queue} "
            f"CLOSE_AT::{state['request']['query_time']} LATER_SUBMISSIONS::DEFER",
        )
    if style == "STATE_DELTA_PACKET":
        return (
            "application/json;profile=state-delta-packet-v1",
            canonical({
                "domain": domain,
                "decision_clock": state["request"]["query_time"],
                "initial_state": visible,
                "submitted_events_unordered": events,
                "execution_rule": ["time", "priority", "sequence", "event_id"],
                "late_event_rule": "defer",
            }),
        )
    if style == "QUEUE_CONTROL_SHEET":
        queue = "\n".join(f"CONTROL_LINE[{event_text(event)}]" for event in events)
        return (
            "text/plain;profile=queue-control-sheet-v1",
            f"QUEUE CONTROL SHEET — {domain}\nCutoff: {state['request']['query_time']}\n"
            f"Initial typed state: {canonical(visible)}\nUnsorted submissions:\n{queue}\n"
            "Sort all submissions canonically; execute through the cutoff and retain later identifiers as deferred.",
        )
    if style == "CROSS_FORMAT_REGISTER":
        queue = " ".join(f"REGISTER_ENTRY[{event_text(event)}]" for event in events)
        return (
            "text/plain;profile=cross-format-register-v1",
            f"Cross-format register for {domain}. The controlling clock is {state['request']['query_time']}. "
            f"Begin from typed state {canonical(visible)}. Entries are submitted out of order. Apply the "
            f"time/priority/sequence/identifier order only through the controlling clock; preserve all later "
            f"entries as deferred. {queue}",
        )
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
    if style == "AUDIT_PACKET":
        queue = "\n".join(f"ENTRY::{event_text(event)}" for event in events)
        content = (
            f"AUDIT_PACKET domain={domain}\n"
            f"DISPOSITION_TIME={state['request']['query_time']}\n"
            f"INITIAL_STATE={canonical(visible)}\n"
            f"SUBMITTED_QUEUE_BEGIN\n{queue}\nSUBMITTED_QUEUE_END"
        )
        return "text/plain;profile=audit-packet-v1", content
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
            "content_sha256": digest({"style": style, "schema": "actionnet-event-render-v9"}),
            "parents": [],
            "authority": "EDON Research Lab",
            "transformation": "render-eventnet-v7",
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
    generator_profile: str,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    trajectories: list[dict[str, Any]] = []
    pairs: list[dict[str, Any]] = []
    lineages: list[dict[str, Any]] = []
    generator_lineage = opaque("generator", PROTOCOL_ID, generator_profile, split, seed)
    lineages.append({
        "lineage_id": generator_lineage,
        "lineage_type": "generator",
        "version": "1.0.0",
        "content_sha256": digest({"protocol": PROTOCOL_ID, "profile": generator_profile, "split": split, "seed": seed, "implementation": "multigen-eventnet-v1"}),
        "parents": ["ACTIONNET-DATA-QUAL-007-result-v1.0.0"],
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
    decision_clock_violations = 0
    deferred_counts: Counter[int] = Counter()
    executed_counts: Counter[int] = Counter()
    query_times: Counter[int] = Counter()
    mutation_path_counts: Counter[int] = Counter()
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
                "transformation": "project-authored-synthetic-source-v7",
            },
            {
                "lineage_id": institution_lineage,
                "lineage_type": "institution",
                "version": "1.0.0",
                "content_sha256": digest(config),
                "parents": [source_lineage],
                "authority": "EDON Research Lab",
                "transformation": "compile-institution-v7",
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
                mechanism = FOCUSED_PIVOTAL_SCHEDULE[pivotal_counter % len(FOCUSED_PIVOTAL_SCHEDULE)]
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
                deferred_counts[len(receipt["deferred_event_ids"])] += 1
                executed_counts[len(receipt["executed_event_ids"])] += 1
                query_times[variant_state["request"]["query_time"]] += 1
                ordered_by_id = {event["event_id"]: event for event in events}
                decision_clock_violations += sum(
                    ordered_by_id[event_id]["time"] <= variant_state["request"]["query_time"]
                    for event_id in receipt["deferred_event_ids"]
                )
                decision_clock_violations += sum(
                    ordered_by_id[event_id]["time"] > variant_state["request"]["query_time"]
                    for event_id in receipt["executed_event_ids"]
                )
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
                    "generator_profile": generator_profile,
                    "pair_class": pair_class,
                    "variant": variant,
                    "intervention_family": intervention_family,
                    "pair_mechanism": mechanism,
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
                mutation_path_counts[len(trajectory["changed_fields"])] += 1
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
        "deferred_event_count_distribution": dict(sorted(deferred_counts.items())),
        "executed_event_count_distribution": dict(sorted(executed_counts.items())),
        "decision_clock_violations": decision_clock_violations,
        "query_time_distribution": dict(sorted(query_times.items())),
        "mutation_path_count_distribution": dict(sorted(mutation_path_counts.items())),
        "multi_actor_trajectories": multi_actor,
        "cross_institution_trajectories": cross_institution,
        "families": sorted(families),
        "generator_lineage": generator_lineage,
        "generator_profile": generator_profile,
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
        "sample_weight": sample_weight,
        "training_fields": ["input", "target"],
    }


def compact_step_semantics(receipt: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "event_id": step["event_id"],
            "operation": step["operation"],
            "semantic_state": step["semantic_state"],
            "decision": step["decision"],
        }
        for step in receipt["step_semantics"]
    ]


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
                    0.5,
                ),
                (
                    "TRANSITION",
                    "Apply the queue and return exactly: post_state, semantic_state, decision, failed_conditions, and binding_authority=false. Digests and changed fields are derived deterministically after generation.",
                    {
                        "post_state": public_state(trajectory["final_state"]),
                        "semantic_state": trajectory["outcome"]["semantic_state"],
                        "decision": trajectory["outcome"]["decision"],
                        "failed_conditions": trajectory["outcome"]["failed_conditions"],
                        "binding_authority": False,
                    },
                    3.0,
                ),
                (
                    "QUEUE_TRACE",
                    "Return exactly: ordered_event_ids, executed_event_ids, deferred_event_ids, compact step_semantics, final_state, and binding_authority=false. Do not calculate hashes.",
                    {
                        "ordered_event_ids": trajectory["execution_receipt"]["ordered_event_ids"],
                        "executed_event_ids": trajectory["execution_receipt"]["executed_event_ids"],
                        "deferred_event_ids": trajectory["execution_receipt"]["deferred_event_ids"],
                        "step_semantics": compact_step_semantics(trajectory["execution_receipt"]),
                        "final_state": public_state(trajectory["final_state"]),
                        "binding_authority": False,
                    },
                    4.0,
                ),
            )
            for task_type, query, target, task_multiplier in tasks:
                deferral_multiplier = (
                    1.0 + 0.25 * len(trajectory["execution_receipt"]["deferred_event_ids"])
                    if weighted and task_type == "QUEUE_TRACE"
                    else 1.0
                )
                records.append({
                    "case_id": opaque("case", PROTOCOL_ID, trajectory["trajectory_id"], style, task_type),
                    "input": {"observation": obs, "query": query},
                    "target": target,
                    "metadata": metadata(
                        trajectory,
                        style,
                        task_type,
                        round(weight * task_multiplier * deferral_multiplier, 6),
                    ),
                })
    for pair in pairs:
        base_trajectory = pair["base"]
        comparison = pair["comparison"]
        pair_weight = (5.0 if pair["pair_class"] == "PIVOTAL" else 2.5) if weighted else 1.0
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
                    "query": "Execute both queues and return exactly: decision_changed, both certificates, causal_event_change_paths, changed_post_state_paths, and binding_authority=false.",
                },
                "target": {
                    "decision_changed": base_trajectory["outcome"]["decision"] != comparison["outcome"]["decision"],
                    "base_certificate": base_trajectory["outcome"],
                    "comparison_certificate": comparison["outcome"],
                    "causal_event_change_paths": sorted(changed_fields(base_trajectory["submitted_events"], comparison["submitted_events"])),
                    "changed_post_state_paths": sorted(changed_fields(base_trajectory["final_state"], comparison["final_state"])),
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
    if weighted:
        decision_totals: Counter[str] = Counter()
        for record in records:
            if record["metadata"]["task_type"] != "PAIR_CONTRAST":
                decision_totals[record["metadata"]["decision"]] += record["metadata"]["sample_weight"]
        target_total = max(decision_totals.values())
        normalization = {decision: target_total / total for decision, total in decision_totals.items()}
        for record in records:
            if record["metadata"]["task_type"] != "PAIR_CONTRAST":
                decision = record["metadata"]["decision"]
                record["metadata"]["sample_weight"] = round(
                    record["metadata"]["sample_weight"] * normalization[decision], 6
                )
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


def combine_split_audits(profile_audits: dict[str, dict[str, Any]]) -> dict[str, Any]:
    distribution_keys = ("pair_class_distribution","mechanism_distribution","decision_distribution","deferred_event_count_distribution","executed_event_count_distribution","query_time_distribution","mutation_path_count_distribution")
    numeric_keys = ("engine_comparisons","engine_disagreements","scheduler_disagreements","transition_disagreements","pivotal_pair_changes","invariance_pair_changes","contextual_pair_changes","aggregation_equivalence_checks","aggregation_equivalence_failures","simultaneous_event_trajectories","deferred_event_trajectories","decision_clock_violations","multi_actor_trajectories","cross_institution_trajectories")
    combined = {key: sum(int(audit[key]) for audit in profile_audits.values()) for key in numeric_keys}
    for key in distribution_keys:
        counts: Counter[Any] = Counter()
        for audit in profile_audits.values(): counts.update(audit[key])
        combined[key] = dict(sorted(counts.items(), key=lambda item: str(item[0])))
    combined["families"] = sorted({f for audit in profile_audits.values() for f in audit["families"]})
    combined["generator_lineages"] = sorted(a["generator_lineage"] for a in profile_audits.values())
    combined["generator_profiles"] = sorted(profile_audits)
    combined["aggregate_outcome_sha256"] = digest({p:a["aggregate_outcome_sha256"] for p,a in sorted(profile_audits.items())})
    return combined

def historical_overlap(case_ids: set[str], prompt_hashes: set[str]) -> dict[str, int]:
    reference = json.loads((ROOT / "oracle" / "actionnet007_overlap_reference.json").read_text())
    content_hash = reference.pop("content_sha256", None)
    if content_hash != digest(reference): raise ValueError("ActionNet-007 overlap reference hash mismatch")
    return {"actionnet_007_case_overlap":len(case_ids & set(reference["case_ids"])),"actionnet_007_prompt_overlap":len(prompt_hashes & set(reference["prompt_hashes"]))}


def generate() -> dict[str, Any]:
    renderer_ids, lineages = renderer_lineages()
    ledger_trajectories, ledger_pairs, ledger_lineages, ledger_audit = generate_split("train", LEDGER_SEED, tuple(range(300,312)), 32, ("permit-control","procurement-routing","research-operations","service-allocation"), "LEDGER")
    matrix_trajectories, matrix_pairs, matrix_lineages, matrix_audit = generate_split("train", MATRIX_SEED, tuple(range(312,324)), 32, ("credential-review","capacity-governance","appeal-routing","evidence-control"), "MATRIX")
    validation_trajectories, validation_pairs, validation_lineages, validation_audit = generate_split(
        "repair_validation", VALIDATION_SEED, tuple(range(340,346)), 32,
        ("aviation-governance","water-review","identity-appeals"), "GRAPH"
    )
    train_trajectories = ledger_trajectories + matrix_trajectories; train_pairs = ledger_pairs + matrix_pairs
    train_audit = combine_split_audits({"LEDGER":ledger_audit,"MATRIX":matrix_audit})
    lineages.extend(ledger_lineages + matrix_lineages + validation_lineages)
    train_records = make_records(ledger_trajectories, ledger_pairs, TRAIN_RENDERERS_LEDGER, renderer_ids, weighted=True) + make_records(matrix_trajectories, matrix_pairs, TRAIN_RENDERERS_MATRIX, renderer_ids, weighted=True)
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
    queue_train_records = [row for row in train_records if row["metadata"]["task_type"] == "QUEUE_TRACE"]
    pair_train_records = [row for row in train_records if row["metadata"]["task_type"] == "PAIR_CONTRAST"]
    event_visibility = 0
    minimum_queue_length = min(len(trajectory["submitted_events"]) for trajectory in all_trajectories)
    for trajectory in train_trajectories:
        for style in (TRAIN_RENDERERS_LEDGER if trajectory["generator_profile"] == "LEDGER" else TRAIN_RENDERERS_MATRIX):
            _, content = render(style, trajectory["domain"], trajectory["initial_state"], trajectory["submitted_events"])
            event_visibility += int(not event_operands_visible(content, trajectory["submitted_events"]))
    for trajectory in validation_trajectories:
        _, content = render(VALIDATION_RENDERER, trajectory["domain"], trajectory["initial_state"], trajectory["submitted_events"])
        event_visibility += int(not event_operands_visible(content, trajectory["submitted_events"]))

    case_ids = {row["case_id"] for row in all_records}
    historical = historical_overlap(case_ids, train_prompt_hashes | validation_prompt_hashes)
    protected = {
        "actionnet_004_train_semantic_families": list(range(30, 42)),
        "actionnet_004_repair_validation_semantic_families": list(range(50, 54)),
        "eventnet_repair_train_semantic_families": list(range(70, 82)),
        "eventnet_fresh_validation_semantic_families": list(range(90, 94)),
        "appeal_repair_train_semantic_families": list(range(110, 126)),
        "appeal_repair_validation_semantic_families": list(range(140, 148)),
        "execution_repair_train_semantic_families": list(range(180, 204)),
        "execution_repair_validation_semantic_families": list(range(220, 228)),
        "multigen_repair_train_semantic_families": list(range(300,324)),
        "multigen_repair_validation_semantic_families": list(range(340,346)),
        "future_public_semantic_families": list(range(360,366)),
        "protected_semantic_families": list(range(370,376)),
        "public_materialized": False,
        "protected_materialized": False,
        "real_institution_materialized": False,
    }
    audits = {
        "train": train_audit,
        "train_by_generator": {"LEDGER":ledger_audit,"MATRIX":matrix_audit},
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
        "train_generator_profiles": sorted({row["metadata"]["generator_profile"] for row in train_records}),
        "repair_validation_generator_profiles": sorted({row["metadata"]["generator_profile"] for row in validation_records}),
        "queue_train_record_count": len(queue_train_records),
        "pair_train_record_count": len(pair_train_records),
        **historical,
    }
    expected_train_pairs = 24 * 32
    expected_validation_pairs = 6 * 32
    expected_train_records = expected_train_pairs * (2 * 3 + 1) * 2
    expected_validation_records = expected_validation_pairs * (2 * 3 + 1)
    controls = {
        "registered_counts": len(train_records) == expected_train_records and len(validation_records) == expected_validation_records and len(all_trajectories) == 1920 and len(all_pairs) == 960,
        "independent_reference_engines_exact": train_audit["engine_disagreements"] == 0 and validation_audit["engine_disagreements"] == 0,
        "independent_schedulers_exact": train_audit["scheduler_disagreements"] == 0 and validation_audit["scheduler_disagreements"] == 0,
        "transitions_exact": train_audit["transition_disagreements"] == 0 and validation_audit["transition_disagreements"] == 0,
        "pivotal_pairs_change": train_audit["pivotal_pair_changes"] == train_audit["pair_class_distribution"]["PIVOTAL"] and validation_audit["pivotal_pair_changes"] == validation_audit["pair_class_distribution"]["PIVOTAL"],
        "invariance_pairs_preserve": train_audit["invariance_pair_changes"] == 0 and validation_audit["invariance_pair_changes"] == 0,
        "contextual_pairs_preserve": train_audit["contextual_pair_changes"] == 0 and validation_audit["contextual_pair_changes"] == 0,
        "all_pivotal_mechanisms_covered": set(PIVOTAL_MECHANISMS).issubset(train_audit["mechanism_distribution"]) and set(PIVOTAL_MECHANISMS).issubset(validation_audit["mechanism_distribution"]),
        "multi_step_queues": minimum_queue_length >= 4,
        "simultaneous_events_present": train_audit["simultaneous_event_trajectories"] > 0 and validation_audit["simultaneous_event_trajectories"] > 0,
        "deferral_on_every_trajectory": train_audit["deferred_event_trajectories"] == len(train_trajectories) and validation_audit["deferred_event_trajectories"] == len(validation_trajectories),
        "decision_clock_exact": train_audit["decision_clock_violations"] == 0 and validation_audit["decision_clock_violations"] == 0,
        "variable_decision_clocks": len(train_audit["query_time_distribution"]) == 5 and len(validation_audit["query_time_distribution"]) == 5,
        "executed_and_deferred_events_coexist": min(train_audit["executed_event_count_distribution"]) >= 5 and min(validation_audit["executed_event_count_distribution"]) >= 5,
        "multi_path_state_mutation": min(train_audit["mutation_path_count_distribution"]) >= 2 and min(validation_audit["mutation_path_count_distribution"]) >= 2,
        "multi_actor_trajectories": train_audit["multi_actor_trajectories"] == len(train_trajectories) and validation_audit["multi_actor_trajectories"] == len(validation_trajectories),
        "cross_institution_coverage": train_audit["cross_institution_trajectories"] > 0 and validation_audit["cross_institution_trajectories"] > 0,
        "safe_aggregation_equivalence": train_audit["aggregation_equivalence_checks"] > 0 and validation_audit["aggregation_equivalence_checks"] > 0 and train_audit["aggregation_equivalence_failures"] == 0 and validation_audit["aggregation_equivalence_failures"] == 0,
        "all_task_types_present": set(audits["task_types"]) == set(TASK_TYPES),
        "four_training_renderers": set(audits["train_renderers"]) == set(TRAIN_RENDERERS),
        "heldout_renderer_unseen_in_train": set(audits["repair_validation_renderers"]).isdisjoint(audits["train_renderers"]),
        "event_operands_visible": event_visibility == 0,
        "zero_training_prompt_conflicts": train_record_audit["conflicting_prompt_groups"] == 0,
        "zero_validation_prompt_conflicts": validation_record_audit["conflicting_prompt_groups"] == 0,
        "model_inputs_metadata_free": train_record_audit["forbidden_model_inputs"] == 0 and validation_record_audit["forbidden_model_inputs"] == 0,
        "no_decision_labels_in_inputs": train_record_audit["decision_label_tokens_in_inputs"] == 0 and validation_record_audit["decision_label_tokens_in_inputs"] == 0,
        "train_validation_prompts_disjoint": audits["train_validation_prompt_overlap"] == 0,
        "lineages_disjoint": all(audits[key] == 0 for key in ("trajectory_overlap", "pair_overlap", "institution_overlap", "source_overlap", "generator_overlap", "semantic_family_overlap", "authority_graph_overlap", "workflow_graph_overlap")),
        "actionnet_007_not_reused": audits["actionnet_007_case_overlap"] == 0 and audits["actionnet_007_prompt_overlap"] == 0,
        "queue_supervision_dominant": sum(row["metadata"]["sample_weight"] for row in queue_train_records) > 2 * sum(row["metadata"]["sample_weight"] for row in train_records if row["metadata"]["task_type"] == "CERTIFICATE"),
        "pair_diff_supervision_present": len(pair_train_records) == expected_train_pairs * 2,
        "effective_decision_weights_balanced": max(train_record_audit["effective_weighted_decisions"].values()) - min(train_record_audit["effective_weighted_decisions"].values()) < 0.01,
        "model_inputs_only_observation_and_query": all(set(row["input"]) == {"observation", "query"} for row in all_records),
        "binding_authority_always_false": all(row["target"].get("binding_authority") is False for row in all_records),
        "future_public_and_protected_unmaterialized": not (set(range(360,366)) | set(range(370,376))) & {item["semantic_family"] for item in all_trajectories},
        "fresh_generator_lineages": set(train_audit["generator_lineages"]).isdisjoint({validation_audit["generator_lineage"]}),
        "two_training_generator_profiles": audits["train_generator_profiles"] == ["LEDGER","MATRIX"],
        "heldout_validation_generator_profile": audits["repair_validation_generator_profiles"] == ["GRAPH"],
        "generator_profile_lineages_disjoint": len(set(train_audit["generator_lineages"]+[validation_audit["generator_lineage"]])) == 3,
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