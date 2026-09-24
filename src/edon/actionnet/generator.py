"""Deterministic ActionNet world generation from approved Institutional IR."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from edon.common.hashing import sha256_json
from edon.runtime import InstitutionalRuntime, expected_facts, validate_approved_mechanism


class ActionNetGenerationError(ValueError):
    pass


def _mutated(value: Any) -> Any:
    if isinstance(value, bool):
        return not value
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return value + 1
    if isinstance(value, str):
        return f"NOT_{value}"
    if value is None:
        return "NOT_NULL"
    return {"mutated_from_sha256": sha256_json(value)}


def _case_id(mechanism: dict[str, Any], scenario: str, identity: Any) -> str:
    digest = sha256_json({
        "mechanism_id": mechanism["mechanism_id"],
        "version": mechanism["version"],
        "scenario": scenario,
        "identity": identity,
    })
    return "case-" + digest.split(":", 1)[1][:20]


def _public_case(
    case_id: str,
    observation: dict[str, Any],
    query: str,
    task_type: str,
    institution_lineage: str,
    source_lineage: str,
) -> dict[str, Any]:
    return {
        "case_id": case_id,
        "observation": observation,
        "query": query,
        "task_type": task_type,
        "institution_lineage": institution_lineage,
        "source_lineage": source_lineage,
    }


def generate_actionnet(mechanism: dict[str, Any], *, generator_seed: int = 0) -> dict[str, Any]:
    """Generate normal, failure, edge, transition, queue, and pair cases."""

    checks = validate_approved_mechanism(mechanism)
    if not all(checks.values()):
        raise ActionNetGenerationError(f"mechanism is not generation-ready: {checks}")
    runtime = InstitutionalRuntime()
    expected = expected_facts(mechanism)
    institution_lineage = f"{mechanism['mechanism_id']}@{mechanism['version']}"
    source_lineage = sha256_json(mechanism.get("source_references", []))
    base_state = {"facts": deepcopy(expected)}
    public_cases: list[dict[str, Any]] = []
    oracle_labels: dict[str, dict[str, Any]] = {}

    normal_id = _case_id(mechanism, "NORMAL", generator_seed)
    normal_certificate = runtime.evaluate(mechanism, base_state).as_dict()
    public_cases.append(_public_case(
        normal_id,
        {"mechanism_id": mechanism["mechanism_id"], "scenario_class": "NORMAL", "state": base_state},
        "Evaluate whether the proposed institutional action is permitted.",
        "CERTIFICATE",
        institution_lineage,
        source_lineage,
    ))
    oracle_labels[normal_id] = normal_certificate

    for index, path in enumerate(sorted(expected)):
        wrong_value = _mutated(expected[path])
        failure_state = {"facts": deepcopy(expected)}
        failure_state["facts"][path] = wrong_value
        failure_id = _case_id(mechanism, "FAILURE", {"path": path, "seed": generator_seed})
        failure_certificate = runtime.evaluate(mechanism, failure_state).as_dict()
        public_cases.append(_public_case(
            failure_id,
            {
                "mechanism_id": mechanism["mechanism_id"],
                "scenario_class": "FAILURE",
                "intervention_path": path,
                "state": failure_state,
            },
            "Evaluate whether the proposed institutional action is permitted.",
            "CERTIFICATE",
            institution_lineage,
            source_lineage,
        ))
        oracle_labels[failure_id] = failure_certificate

        edge_state = {"facts": deepcopy(expected)}
        edge_state["facts"].pop(path)
        edge_id = _case_id(mechanism, "EDGE_MISSING", {"path": path, "seed": generator_seed})
        edge_certificate = runtime.evaluate(mechanism, edge_state).as_dict()
        public_cases.append(_public_case(
            edge_id,
            {
                "mechanism_id": mechanism["mechanism_id"],
                "scenario_class": "EDGE",
                "intervention_path": path,
                "state": edge_state,
            },
            "Evaluate the action when one institutional fact is unavailable.",
            "CERTIFICATE",
            institution_lineage,
            source_lineage,
        ))
        oracle_labels[edge_id] = edge_certificate

        pair_id = "pair-" + sha256_json({"mechanism": institution_lineage, "path": path}).split(":", 1)[1][:20]
        pair_case_id = _case_id(mechanism, "PAIR_CONTRAST", {"path": path, "seed": generator_seed})
        public_cases.append(_public_case(
            pair_case_id,
            {
                "mechanism_id": mechanism["mechanism_id"],
                "scenario_class": "COUNTERFACTUAL",
                "pair_id": pair_id,
                "base": base_state,
                "comparison": failure_state,
                "intervention_path": path,
            },
            "Determine whether and why the institutional decision changes between the two states.",
            "PAIR_CONTRAST",
            institution_lineage,
            source_lineage,
        ))
        oracle_labels[pair_case_id] = {
            "pair_id": pair_id,
            "base_decision": normal_certificate["decision"],
            "comparison_decision": failure_certificate["decision"],
            "decision_changed": normal_certificate["decision"] != failure_certificate["decision"],
            "causal_path": path,
            "binding_authority": False,
        }

        event = {
            "event_id": f"event-{index:04d}-invalidate",
            "sequence": 0,
            "priority": 0,
            "action": "SET",
            "path": path,
            "value": wrong_value,
        }
        transition_id = _case_id(mechanism, "TRANSITION", {"path": path, "seed": generator_seed})
        transition_result = runtime.execute_events(mechanism, base_state, [event])
        public_cases.append(_public_case(
            transition_id,
            {
                "mechanism_id": mechanism["mechanism_id"],
                "scenario_class": "TRANSITION",
                "initial_state": base_state,
                "events": [event],
            },
            "Apply the event and return the resulting state and institutional decision.",
            "TRANSITION",
            institution_lineage,
            source_lineage,
        ))
        oracle_labels[transition_id] = {
            "final_state": transition_result["final_state"],
            "certificate": transition_result["certificate"],
            "binding_authority": False,
        }

    first_path = sorted(expected)[0]
    queue_initial = {"facts": deepcopy(expected)}
    queue_initial["facts"].pop(first_path)
    queue_events = [
        {
            "event_id": "queue-restore-low-priority",
            "sequence": 0,
            "priority": 1,
            "action": "SET",
            "path": first_path,
            "value": _mutated(expected[first_path]),
        },
        {
            "event_id": "queue-restore-authoritative",
            "sequence": 1,
            "priority": 10,
            "action": "SET",
            "path": first_path,
            "value": expected[first_path],
        },
    ]
    queue_id = _case_id(mechanism, "QUEUE_TRACE", {"path": first_path, "seed": generator_seed})
    queue_result = runtime.execute_events(mechanism, queue_initial, queue_events)
    public_cases.append(_public_case(
        queue_id,
        {
            "mechanism_id": mechanism["mechanism_id"],
            "scenario_class": "QUEUE",
            "initial_state": queue_initial,
            "events": queue_events,
        },
        "Execute the event queue in canonical order and return the final state and decision.",
        "QUEUE_TRACE",
        institution_lineage,
        source_lineage,
    ))
    oracle_labels[queue_id] = {
        "event_trace": queue_result["event_trace"],
        "final_state": queue_result["final_state"],
        "certificate": queue_result["certificate"],
        "binding_authority": False,
    }

    public_payload = {"schema_version": "edon-actionnet-public.v1", "cases": public_cases}
    protected_payload = {"schema_version": "edon-actionnet-oracle.v1", "labels": oracle_labels}
    return {
        "schema_version": "edon-actionnet-bundle.v1",
        "mechanism_id": mechanism["mechanism_id"],
        "mechanism_version": mechanism["version"],
        "generator_seed": generator_seed,
        "public": public_payload,
        "protected": protected_payload,
        "manifest": {
            "public_sha256": sha256_json(public_payload),
            "protected_sha256": sha256_json(protected_payload),
            "mechanism_sha256": sha256_json(mechanism),
            "case_count": len(public_cases),
            "label_count": len(oracle_labels),
            "labels_separated": True,
            "deterministic": True,
        },
        "claim_boundary": "Synthetic experience generated from an approved project representation; not observed real-world outcomes.",
    }