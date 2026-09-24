"""Deterministic execution of approved Institutional IR mechanisms."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from typing import Any

from edon.common.hashing import sha256_json
from edon.ir import Decision, SemanticState


class RuntimeExecutionError(ValueError):
    pass


@dataclass(frozen=True)
class ExecutionCertificate:
    mechanism_id: str
    mechanism_version: str
    semantic_state: SemanticState
    decision: Decision
    failed_conditions: tuple[str, ...]
    evaluated_conditions: int
    final_state_sha256: str
    trace: tuple[dict[str, Any], ...] = ()
    binding_authority: bool = False

    def __post_init__(self) -> None:
        if self.binding_authority:
            raise RuntimeExecutionError("runtime certificates cannot grant binding authority")

    def as_dict(self) -> dict[str, Any]:
        return {
            "mechanism_id": self.mechanism_id,
            "mechanism_version": self.mechanism_version,
            "semantic_state": self.semantic_state.value,
            "decision": self.decision.value,
            "failed_conditions": list(self.failed_conditions),
            "evaluated_conditions": self.evaluated_conditions,
            "final_state_sha256": self.final_state_sha256,
            "trace": list(self.trace),
            "binding_authority": False,
        }


def fact_path(fact: dict[str, Any]) -> str:
    return f"{fact['subject']}.{fact['predicate']}"


def expected_facts(mechanism: dict[str, Any]) -> dict[str, Any]:
    facts = mechanism.get("facts")
    if not isinstance(facts, list) or not facts:
        raise RuntimeExecutionError("approved mechanism contains no executable facts")
    expected: dict[str, Any] = {}
    for fact in facts:
        if not isinstance(fact, dict) or fact.get("selected_value") is None:
            raise RuntimeExecutionError("approved mechanism contains an unresolved fact")
        path = fact_path(fact)
        if path in expected and expected[path] != fact["selected_value"]:
            raise RuntimeExecutionError(f"approved mechanism contains contradictory fact: {path}")
        expected[path] = fact["selected_value"]
    return expected


def validate_approved_mechanism(mechanism: dict[str, Any]) -> dict[str, bool]:
    metadata = mechanism.get("metadata", {})
    conflict_count = int(metadata.get("conflict_count", 0))
    resolved = metadata.get("resolved_conflicts", {})
    checks = {
        "approved_true": mechanism.get("approved") is True,
        "binding_authority_false": mechanism.get("binding_authority") is False,
        "source_references_present": bool(mechanism.get("source_references")),
        "facts_present": bool(mechanism.get("facts")),
        "conflicts_resolved": conflict_count == 0 or len(resolved) >= conflict_count,
    }
    if checks["facts_present"]:
        try:
            expected_facts(mechanism)
        except RuntimeExecutionError:
            checks["facts_consistent"] = False
        else:
            checks["facts_consistent"] = True
    else:
        checks["facts_consistent"] = False
    return checks


class InstitutionalRuntime:
    """Pure deterministic evaluator; external commit authority remains separate."""

    def evaluate(self, mechanism: dict[str, Any], state: dict[str, Any]) -> ExecutionCertificate:
        checks = validate_approved_mechanism(mechanism)
        if not all(checks.values()):
            raise RuntimeExecutionError(f"mechanism failed runtime validation: {checks}")
        observed = state.get("facts")
        if not isinstance(observed, dict):
            raise RuntimeExecutionError("runtime state must contain a facts object")
        expected = expected_facts(mechanism)
        missing: list[str] = []
        mismatched: list[str] = []
        trace: list[dict[str, Any]] = []
        for path in sorted(expected):
            if path not in observed:
                missing.append(f"MISSING:{path}")
                trace.append({"path": path, "status": "MISSING", "expected": expected[path]})
            elif observed[path] != expected[path]:
                mismatched.append(f"MISMATCH:{path}")
                trace.append({
                    "path": path,
                    "status": "MISMATCH",
                    "expected": expected[path],
                    "observed": observed[path],
                })
            else:
                trace.append({"path": path, "status": "SATISFIED", "expected": expected[path]})
        if missing:
            semantic_state = SemanticState.MISSING
            decision = Decision.ABSTAIN
            failed = tuple(missing + mismatched)
        elif mismatched:
            semantic_state = SemanticState.FALSE
            decision = Decision.DENY
            failed = tuple(mismatched)
        else:
            semantic_state = SemanticState.TRUE
            decision = Decision.ALLOW
            failed = ()
        return ExecutionCertificate(
            mechanism_id=str(mechanism["mechanism_id"]),
            mechanism_version=str(mechanism["version"]),
            semantic_state=semantic_state,
            decision=decision,
            failed_conditions=failed,
            evaluated_conditions=len(expected),
            final_state_sha256=sha256_json(state),
            trace=tuple(trace),
            binding_authority=False,
        )

    def execute_events(
        self,
        mechanism: dict[str, Any],
        initial_state: dict[str, Any],
        events: list[dict[str, Any]],
    ) -> dict[str, Any]:
        checks = validate_approved_mechanism(mechanism)
        if not all(checks.values()):
            raise RuntimeExecutionError(f"mechanism failed runtime validation: {checks}")
        state = deepcopy(initial_state)
        if not isinstance(state.get("facts"), dict):
            raise RuntimeExecutionError("initial state must contain a facts object")
        event_ids: set[str] = set()
        normalized: list[dict[str, Any]] = []
        for index, event in enumerate(events):
            event_id = str(event.get("event_id", ""))
            if not event_id or event_id in event_ids:
                raise RuntimeExecutionError("events require unique non-empty event_id values")
            event_ids.add(event_id)
            action = event.get("action")
            if action not in {"SET", "DELETE"}:
                raise RuntimeExecutionError(f"unsupported event action at index {index}")
            normalized.append({
                **event,
                "sequence": int(event.get("sequence", index)),
                "priority": int(event.get("priority", 0)),
            })
        ordered = sorted(normalized, key=lambda row: (row["sequence"], -row["priority"], row["event_id"]))
        event_trace: list[dict[str, Any]] = []
        for event in ordered:
            path = str(event.get("path", ""))
            if not path:
                raise RuntimeExecutionError("event path is required")
            before = state["facts"].get(path, "__MISSING__")
            if event["action"] == "SET":
                state["facts"][path] = event.get("value")
            else:
                state["facts"].pop(path, None)
            event_trace.append({
                "event_id": event["event_id"],
                "sequence": event["sequence"],
                "priority": event["priority"],
                "action": event["action"],
                "path": path,
                "before": before,
                "after": state["facts"].get(path, "__MISSING__"),
            })
        certificate = self.evaluate(mechanism, state)
        return {
            "mechanism_id": mechanism["mechanism_id"],
            "mechanism_version": mechanism["version"],
            "initial_state_sha256": sha256_json(initial_state),
            "events_sha256": sha256_json(ordered),
            "event_trace": event_trace,
            "final_state": state,
            "certificate": certificate.as_dict(),
            "binding_authority": False,
        }