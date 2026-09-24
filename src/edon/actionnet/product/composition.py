"""Executable, bounded ActionNet mechanism composition over canonical Institutional IR."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from edon.common.hashing import sha256_json

from .institutional import InstitutionalIRValidator


class CompositionExecutionError(ValueError):
    """Raised when registered mechanisms cannot form a valid executable composition."""


EXECUTABLE_RELATIONS = {
    "COMPOSES_WITH", "AMPLIFIES", "MITIGATES", "INHIBITS", "PRECONDITION_FOR", "CAUSES"
}
OPERATIONS = {"SET", "DELETE", "INCREMENT", "DECREMENT", "MULTIPLY"}


def _mechanism_key(reference: dict[str, Any]) -> str:
    return f"{reference['mechanism_id']}@{reference['version']}"


def _deepcopy_json(value: Any) -> Any:
    return deepcopy(value)


def _initial_state(ir: dict[str, Any]) -> dict[str, Any]:
    return {
        "time_seconds": 0,
        "objects": {
            item["object_id"]: {
                "object_type": item["object_type"],
                "attributes": _deepcopy_json(item["attributes"]),
                "epistemic_state": _deepcopy_json(item["epistemic_state"]),
                **(
                    {"behavior_model": _deepcopy_json(item["behavior_model"])}
                    if item["object_type"] == "ACTOR" else {}
                ),
            }
            for item in ir["objects"]
        },
    }


def apply_event(state: dict[str, Any], event: dict[str, Any]) -> dict[str, Any]:
    result = _deepcopy_json(state)
    target = str(event["target_object_id"])
    attribute = str(event["attribute"])
    operation = str(event["operation"]).upper()
    if target not in result["objects"]:
        raise CompositionExecutionError(f"transition target does not exist: {target}")
    attributes = result["objects"][target]["attributes"]
    before = attributes.get(attribute, "__MISSING__")
    value = event.get("value")
    if operation == "SET":
        attributes[attribute] = _deepcopy_json(value)
    elif operation == "DELETE":
        attributes.pop(attribute, None)
    elif operation in {"INCREMENT", "DECREMENT", "MULTIPLY"}:
        if isinstance(before, bool) or not isinstance(before, (int, float)):
            raise CompositionExecutionError(
                f"numeric transition requires numeric existing value: {target}.{attribute}"
            )
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise CompositionExecutionError("numeric transition value must be numeric")
        if operation == "INCREMENT":
            attributes[attribute] = before + value
        elif operation == "DECREMENT":
            attributes[attribute] = before - value
        else:
            attributes[attribute] = before * value
    else:
        raise CompositionExecutionError(f"unsupported transition operation: {operation}")
    result["time_seconds"] = int(event["at_seconds"])
    return result


def replay_trajectory(
    initial_state: dict[str, Any], events: list[dict[str, Any]], horizons: list[dict[str, Any]]
) -> dict[str, Any]:
    ordered = sorted(
        _deepcopy_json(events),
        key=lambda row: (int(row["at_seconds"]), int(row.get("order", 0)), str(row["event_id"])),
    )
    ids = [str(event["event_id"]) for event in ordered]
    if len(ids) != len(set(ids)):
        raise CompositionExecutionError("composition events require unique event_id values")
    state = _deepcopy_json(initial_state)
    intermediate = []
    horizon_states = []
    event_index = 0
    for horizon in horizons:
        horizon_seconds = int(horizon["duration_seconds"])
        while event_index < len(ordered) and int(ordered[event_index]["at_seconds"]) <= horizon_seconds:
            event = ordered[event_index]
            before_hash = sha256_json(state)
            state = apply_event(state, event)
            intermediate.append({
                "event_id": event["event_id"],
                "at_seconds": event["at_seconds"],
                "before_sha256": before_hash,
                "after_sha256": sha256_json(state),
                "state": _deepcopy_json(state),
            })
            event_index += 1
        snapshot = _deepcopy_json(state)
        snapshot["time_seconds"] = horizon_seconds
        horizon_states.append({
            "horizon_id": horizon["horizon_id"],
            "duration_seconds": horizon_seconds,
            "state": snapshot,
            "state_sha256": sha256_json(snapshot),
        })
    while event_index < len(ordered):
        event = ordered[event_index]
        before_hash = sha256_json(state)
        state = apply_event(state, event)
        intermediate.append({
            "event_id": event["event_id"],
            "at_seconds": event["at_seconds"],
            "before_sha256": before_hash,
            "after_sha256": sha256_json(state),
            "state": _deepcopy_json(state),
        })
        event_index += 1
    return {
        "initial_state": _deepcopy_json(initial_state),
        "events": ordered,
        "intermediate_states": intermediate,
        "horizon_states": horizon_states,
        "final_state": state,
        "final_state_sha256": sha256_json(state),
    }


class MechanismCompositionEngine:
    """Instantiates registered mechanism compositions and replays their transitions."""

    def _order(self, keys: list[str], edges: list[dict[str, Any]]) -> list[str]:
        incoming = {key: set() for key in keys}
        outgoing = {key: set() for key in keys}
        for edge in edges:
            if edge["relation_type"] not in {"CAUSES", "PRECONDITION_FOR"}:
                continue
            source = _mechanism_key(edge["source"])
            target = _mechanism_key(edge["target"])
            outgoing[source].add(target)
            incoming[target].add(source)
        ready = sorted(key for key in keys if not incoming[key])
        ordered = []
        while ready:
            key = ready.pop(0)
            ordered.append(key)
            for target in sorted(outgoing[key]):
                incoming[target].discard(key)
                if not incoming[target] and target not in ready and target not in ordered:
                    ready.append(target)
                    ready.sort()
        if len(ordered) != len(keys):
            raise CompositionExecutionError("causal composition contains a cycle")
        return ordered

    def compose(
        self,
        run_id: str,
        institutional_ir: dict[str, Any],
        mechanisms: list[dict[str, Any]],
        edges: list[dict[str, Any]],
        *,
        seed: int = 0,
    ) -> dict[str, Any]:
        ir = InstitutionalIRValidator().normalize(institutional_ir)
        if not mechanisms:
            raise CompositionExecutionError("composition requires at least one mechanism")
        mechanism_map = {
            f"{item['mechanism_id']}@{item['version']}": item for item in mechanisms
        }
        if len(mechanism_map) != len(mechanisms):
            raise CompositionExecutionError("composition contains duplicate mechanism versions")
        keys = sorted(mechanism_map)
        edge_ids = set()
        modifiers: dict[str, float] = {key: 1.0 for key in keys}
        inhibited: set[str] = set()
        for edge in edges:
            edge_id = str(edge["edge_id"])
            if edge_id in edge_ids:
                raise CompositionExecutionError(f"duplicate composition edge: {edge_id}")
            edge_ids.add(edge_id)
            relation = str(edge["relation_type"]).upper()
            if relation not in EXECUTABLE_RELATIONS:
                raise CompositionExecutionError(f"relation is not executable: {relation}")
            source = _mechanism_key(edge["source"])
            target = _mechanism_key(edge["target"])
            if source not in mechanism_map or target not in mechanism_map:
                raise CompositionExecutionError("composition edge endpoint is outside the selected mechanisms")
            conditions = edge.get("conditions", {})
            required_types = {str(item).upper() for item in conditions.get("required_object_types", [])}
            available_types = {item["object_type"] for item in ir["objects"]}
            if not required_types.issubset(available_types):
                raise CompositionExecutionError(
                    f"composition edge {edge_id} is missing required Institutional IR object types"
                )
            minimum_horizon = int(conditions.get("minimum_horizon_seconds", 0))
            if minimum_horizon and max(row["duration_seconds"] for row in ir["horizons"]) < minimum_horizon:
                raise CompositionExecutionError(
                    f"composition edge {edge_id} exceeds registered Institutional IR horizons"
                )
            if relation == "AMPLIFIES":
                factor = float(conditions.get("magnitude_multiplier", 1.5))
                if not 1 <= factor <= 10:
                    raise CompositionExecutionError("AMPLIFIES magnitude_multiplier must be between 1 and 10")
                modifiers[target] *= factor
            elif relation == "MITIGATES":
                factor = float(conditions.get("magnitude_multiplier", 0.5))
                if not 0 <= factor <= 1:
                    raise CompositionExecutionError("MITIGATES magnitude_multiplier must be between 0 and 1")
                modifiers[target] *= factor
            elif relation == "INHIBITS" and bool(conditions.get("inhibit_target", True)):
                inhibited.add(target)
        order = self._order(keys, edges)
        objects_by_type: dict[str, list[str]] = {}
        for item in ir["objects"]:
            objects_by_type.setdefault(item["object_type"], []).append(item["object_id"])
        events = []
        causal_steps = []
        for order_index, key in enumerate(order):
            mechanism = mechanism_map[key]
            specification = mechanism["specification"]
            requirements = {str(item).upper() for item in specification.get("ir_requirements", [])}
            missing = sorted(requirements - set(objects_by_type))
            if missing:
                raise CompositionExecutionError(f"mechanism {key} missing IR requirements: {missing}")
            if key in inhibited:
                causal_steps.append({"mechanism_ref": key, "status": "INHIBITED", "event_ids": []})
                continue
            event_ids = []
            for transition_index, transition in enumerate(specification.get("state_transitions", [])):
                if not isinstance(transition, dict) or "operation" not in transition:
                    continue
                operation = str(transition["operation"]).upper()
                if operation not in OPERATIONS:
                    raise CompositionExecutionError(f"unsupported operation in {key}: {operation}")
                target = transition.get("target_object_id")
                if not target:
                    target_type = str(transition.get("target_object_type", "")).upper()
                    candidates = sorted(objects_by_type.get(target_type, []))
                    if not candidates:
                        raise CompositionExecutionError(
                            f"mechanism {key} cannot bind target_object_type {target_type}"
                        )
                    target = candidates[0]
                value = _deepcopy_json(transition.get("value"))
                if operation in {"INCREMENT", "DECREMENT"} and isinstance(value, (int, float)) and not isinstance(value, bool):
                    value *= modifiers[key]
                event_id = f"{run_id}:{order_index:03d}:{transition_index:03d}"
                events.append({
                    "event_id": event_id,
                    "mechanism_ref": key,
                    "target_object_id": str(target),
                    "attribute": str(transition.get("attribute", "value")),
                    "operation": operation,
                    "value": value,
                    "at_seconds": int(transition.get("at_seconds", order_index)),
                    "order": order_index,
                })
                event_ids.append(event_id)
            if not event_ids:
                raise CompositionExecutionError(
                    f"mechanism {key} has no executable state transition for Platform 002"
                )
            causal_steps.append({"mechanism_ref": key, "status": "EXECUTED", "event_ids": event_ids})
        initial = _initial_state(ir)
        trajectory = replay_trajectory(initial, events, ir["horizons"])
        replay = replay_trajectory(initial, trajectory["events"], ir["horizons"])
        actionability = InstitutionalIRValidator().assess_actionability(ir)
        result = {
            "schema_version": "actionnet-composition-run.v1",
            "run_id": str(run_id),
            "seed": int(seed),
            "institution_ir": {
                "institution_id": ir["institution_id"],
                "version": ir["version"],
                "ir_sha256": ir["ir_sha256"],
            },
            "mechanism_refs": [
                {"mechanism_id": mechanism_map[key]["mechanism_id"], "version": mechanism_map[key]["version"]}
                for key in order
            ],
            "edge_refs": sorted(edge_ids),
            "trajectory": trajectory,
            "causal_trace": {"steps": causal_steps, "ordered_mechanisms": order},
            "actionability": actionability,
            "verification": {
                "deterministic_replay": replay["final_state_sha256"] == trajectory["final_state_sha256"],
                "final_state_sha256": trajectory["final_state_sha256"],
                "registered_semantics_only": True,
            },
            "authoritative": False,
            "binding_authority": False,
        }
        result["run_sha256"] = sha256_json(result)
        return result