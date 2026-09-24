"""Deterministic institutional operations loop over world state and episodic memory."""

from __future__ import annotations

import json
import math
from copy import deepcopy
from datetime import UTC, datetime
from typing import Any, Iterable

from edon.common.hashing import sha256_json
from edon.memory import EpisodicMemoryStore
from edon.world import WorldStateStore


class OperationsError(RuntimeError):
    """Raised when an operational proposal violates registered invariants."""


GOAL_STATUSES = {"PROPOSED", "ACTIVE", "PAUSED", "BLOCKED", "COMPLETED", "FAILED", "CANCELLED"}
PLAN_STATUSES = {"ACTIVE", "PAUSED", "NEEDS_REPLAN", "SUPERSEDED", "COMPLETED", "FAILED", "CANCELLED"}
STEP_STATUSES = {"PENDING", "ASSIGNED", "RUNNING", "SUCCEEDED", "FAILED", "CANCELLED"}
AGENT_STATUSES = {"AVAILABLE", "BUSY", "DEGRADED", "OFFLINE", "RETIRED"}
AGENT_KINDS = {"HUMAN", "SOFTWARE", "ROBOT", "SERVICE"}
OBSERVATION_MODALITIES = {
    "TEXT", "IMAGE", "AUDIO", "VIDEO", "SENSOR", "TELEMETRY",
    "DOCUMENT", "HUMAN_REPORT", "SYSTEM_EVENT",
}

GOAL_TRANSITIONS = {
    "PROPOSED": {"ACTIVE", "CANCELLED"},
    "ACTIVE": {"PAUSED", "BLOCKED", "COMPLETED", "FAILED", "CANCELLED"},
    "PAUSED": {"ACTIVE", "CANCELLED"},
    "BLOCKED": {"ACTIVE", "FAILED", "CANCELLED"},
    "COMPLETED": set(),
    "FAILED": set(),
    "CANCELLED": set(),
}


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _identifier(value: Any, label: str) -> str:
    normalized = str(value).strip()
    if not normalized or len(normalized) > 200:
        raise OperationsError(f"{label} must contain between 1 and 200 characters")
    return normalized


def _timestamp(value: Any, label: str) -> str:
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError as exc:
        raise OperationsError(f"{label} must be an ISO-8601 timestamp") from exc
    if parsed.tzinfo is None:
        raise OperationsError(f"{label} must include a timezone")
    return parsed.astimezone(UTC).isoformat()


def _json_object(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise OperationsError(f"{label} must be a JSON object")
    try:
        json.dumps(value, allow_nan=False)
    except (TypeError, ValueError) as exc:
        raise OperationsError(f"{label} must contain finite JSON values") from exc
    return deepcopy(value)


def _number(value: Any, label: str, *, minimum: float = 0.0) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise OperationsError(f"{label} must be numeric")
    result = float(value)
    if not math.isfinite(result) or result < minimum:
        raise OperationsError(f"{label} must be finite and at least {minimum}")
    return result


def _string_set(values: Iterable[Any], label: str) -> list[str]:
    return sorted({_identifier(value, label) for value in values})


def _operational_state(now: str) -> dict[str, Any]:
    return {
        "schema_version": "edon-operational-state.v1",
        "clock": {"now": now},
        "observations": [],
        "goals": {},
        "plans": {},
        "agents": {},
        "resource_pools": {},
        "outcomes": {},
        "alerts": {},
        "learning_candidates": {},
    }


def _topological_order(steps: dict[str, dict[str, Any]]) -> list[str]:
    incoming = {step_id: set(step["dependencies"]) for step_id, step in steps.items()}
    ready = sorted(step_id for step_id, dependencies in incoming.items() if not dependencies)
    order: list[str] = []
    while ready:
        step_id = ready.pop(0)
        order.append(step_id)
        for candidate in sorted(incoming):
            if step_id in incoming[candidate]:
                incoming[candidate].remove(step_id)
                if not incoming[candidate] and candidate not in order and candidate not in ready:
                    ready.append(candidate)
                    ready.sort()
    if len(order) != len(steps):
        raise OperationsError("plan step dependencies contain a cycle")
    return order


class InstitutionalControlPlane:
    """Reference orchestration layer; all durable changes flow through WorldStateStore."""

    def __init__(self, worlds: WorldStateStore, memory: EpisodicMemoryStore):
        self.worlds = worlds
        self.memory = memory

    def bootstrap_world(
        self,
        tenant_id: str,
        world_id: str,
        institution: dict[str, Any],
        *,
        actor_id: str,
        authorization_ref: str,
        source_lineage: Iterable[str] = (),
        timestamp: str | None = None,
    ) -> dict[str, Any]:
        at = _timestamp(timestamp or _now(), "timestamp")
        initial_state = {
            "institution": _json_object(institution, "institution"),
            "operations": _operational_state(at),
        }
        return self.worlds.create_world(
            tenant_id,
            world_id,
            initial_state,
            actor_id=actor_id,
            authorization_ref=authorization_ref,
            source_lineage=source_lineage,
            timestamp=at,
        )

    def initialize_existing_world(
        self,
        tenant_id: str,
        world_id: str,
        *,
        event_id: str,
        actor_id: str,
        expected_version: int,
        authorization_ref: str,
        timestamp: str | None = None,
    ) -> dict[str, Any]:
        snapshot = self.worlds.get_world(tenant_id, world_id)
        if "operations" in snapshot["state"]:
            raise OperationsError("world already contains operational state")
        at = _timestamp(timestamp or _now(), "timestamp")
        return self.worlds.append_event(
            tenant_id,
            world_id,
            event_id,
            "OPERATIONS_INITIALIZED",
            [{"op": "SET", "path": ["operations"], "value": _operational_state(at)}],
            actor_id=actor_id,
            expected_version=expected_version,
            authorization_ref=authorization_ref,
            timestamp=at,
        )

    def _snapshot(self, tenant_id: str, world_id: str) -> tuple[dict[str, Any], dict[str, Any]]:
        snapshot = self.worlds.get_world(tenant_id, world_id)
        operations = snapshot["state"].get("operations")
        if not isinstance(operations, dict) or operations.get("schema_version") != "edon-operational-state.v1":
            raise OperationsError("world does not contain initialized EDON operational state")
        return snapshot, deepcopy(operations)

    @staticmethod
    def _clock_mutation(at: str) -> dict[str, Any]:
        return {"op": "SET", "path": ["operations", "clock", "now"], "value": at}

    def operational_state(self, tenant_id: str, world_id: str) -> dict[str, Any]:
        snapshot, operations = self._snapshot(tenant_id, world_id)
        return {
            "tenant_id": snapshot["tenant_id"],
            "world_id": snapshot["world_id"],
            "world_version": snapshot["version"],
            "world_state_sha256": snapshot["state_sha256"],
            "operations": operations,
            "binding_authority": False,
        }

    def ingest_observation(
        self,
        tenant_id: str,
        world_id: str,
        observation_id: str,
        modality: str,
        source_id: str,
        summary: str,
        payload: dict[str, Any],
        *,
        observed_at: str,
        confidence: float,
        sensitivity: str,
        event_id: str,
        actor_id: str,
        expected_version: int,
        authorization_ref: str,
        provenance: dict[str, Any] | None = None,
        retention_until: str | None = None,
        timestamp: str | None = None,
    ) -> dict[str, Any]:
        observation_id = _identifier(observation_id, "observation_id")
        source_id = _identifier(source_id, "source_id")
        modality = str(modality).upper()
        if modality not in OBSERVATION_MODALITIES:
            raise OperationsError(f"unsupported observation modality: {modality}")
        confidence_value = _number(confidence, "confidence")
        if confidence_value > 1:
            raise OperationsError("confidence cannot exceed 1")
        observed = _timestamp(observed_at, "observed_at")
        at = _timestamp(timestamp or _now(), "timestamp")
        reference = {
            "observation_id": observation_id,
            "modality": modality,
            "source_id": source_id,
            "observed_at": observed,
            "confidence": confidence_value,
            "content_sha256": sha256_json(payload),
        }
        memory = self.memory.record_episode(
            tenant_id,
            observation_id,
            world_id,
            "OBSERVATION",
            summary,
            _json_object(payload, "payload"),
            occurred_at=observed,
            sensitivity=sensitivity,
            actor_id=actor_id,
            authorization_ref=authorization_ref,
            provenance={
                **_json_object(provenance or {}, "provenance"),
                "modality": modality,
                "source_id": source_id,
                "confidence": confidence_value,
            },
            retention_until=retention_until,
            timestamp=at,
        )
        snapshot = self.worlds.append_event(
            tenant_id,
            world_id,
            event_id,
            "OBSERVATION_INGESTED",
            [
                {"op": "APPEND_UNIQUE", "path": ["operations", "observations"], "value": reference},
                self._clock_mutation(at),
            ],
            actor_id=actor_id,
            expected_version=expected_version,
            authorization_ref=authorization_ref,
            source_lineage=[f"memory:{observation_id}:{memory['content_sha256']}"],
            timestamp=at,
        )
        return {"observation": reference, "memory": memory, "world": snapshot, "binding_authority": False}

    def register_agent(
        self,
        tenant_id: str,
        world_id: str,
        agent_id: str,
        kind: str,
        capabilities: Iterable[str],
        *,
        event_id: str,
        actor_id: str,
        expected_version: int,
        authorization_ref: str,
        max_concurrent: int = 1,
        relationships: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
        timestamp: str | None = None,
    ) -> dict[str, Any]:
        _, operations = self._snapshot(tenant_id, world_id)
        agent_id = _identifier(agent_id, "agent_id")
        if agent_id in operations["agents"]:
            raise OperationsError("agent is already registered")
        kind = str(kind).upper()
        if kind not in AGENT_KINDS:
            raise OperationsError(f"unsupported agent kind: {kind}")
        max_concurrent = int(max_concurrent)
        if max_concurrent < 1 or max_concurrent > 1000:
            raise OperationsError("max_concurrent must be between 1 and 1000")
        at = _timestamp(timestamp or _now(), "timestamp")
        agent = {
            "agent_id": agent_id,
            "kind": kind,
            "capabilities": _string_set(capabilities, "capability"),
            "status": "AVAILABLE",
            "max_concurrent": max_concurrent,
            "active_tasks": [],
            "relationships": _json_object(relationships or {}, "relationships"),
            "metadata": _json_object(metadata or {}, "metadata"),
            "registered_at": at,
        }
        return self.worlds.append_event(
            tenant_id, world_id, event_id, "AGENT_REGISTERED",
            [
                {"op": "SET", "path": ["operations", "agents", agent_id], "value": agent},
                self._clock_mutation(at),
            ],
            actor_id=actor_id, expected_version=expected_version,
            authorization_ref=authorization_ref, timestamp=at,
        )

    def set_agent_status(
        self,
        tenant_id: str,
        world_id: str,
        agent_id: str,
        status: str,
        *,
        event_id: str,
        actor_id: str,
        expected_version: int,
        authorization_ref: str,
        timestamp: str | None = None,
    ) -> dict[str, Any]:
        _, operations = self._snapshot(tenant_id, world_id)
        agent_id = _identifier(agent_id, "agent_id")
        agent = deepcopy(operations["agents"].get(agent_id))
        if not agent:
            raise OperationsError("agent is not registered")
        status = str(status).upper()
        if status not in AGENT_STATUSES:
            raise OperationsError(f"unsupported agent status: {status}")
        if status == "RETIRED" and agent["active_tasks"]:
            raise OperationsError("agent with active tasks cannot be retired")
        agent["status"] = status
        at = _timestamp(timestamp or _now(), "timestamp")
        return self.worlds.append_event(
            tenant_id, world_id, event_id, "AGENT_STATUS_CHANGED",
            [
                {"op": "SET", "path": ["operations", "agents", agent_id], "value": agent},
                self._clock_mutation(at),
            ],
            actor_id=actor_id, expected_version=expected_version,
            authorization_ref=authorization_ref, timestamp=at,
        )

    def register_resource_pool(
        self,
        tenant_id: str,
        world_id: str,
        resource_id: str,
        capacity: float,
        unit: str,
        *,
        event_id: str,
        actor_id: str,
        expected_version: int,
        authorization_ref: str,
        renewable: bool = True,
        timestamp: str | None = None,
    ) -> dict[str, Any]:
        _, operations = self._snapshot(tenant_id, world_id)
        resource_id = _identifier(resource_id, "resource_id")
        if resource_id in operations["resource_pools"]:
            raise OperationsError("resource pool is already registered")
        at = _timestamp(timestamp or _now(), "timestamp")
        pool = {
            "resource_id": resource_id,
            "capacity": _number(capacity, "capacity"),
            "allocated": 0.0,
            "unit": _identifier(unit, "unit"),
            "renewable": bool(renewable),
            "allocations": {},
            "registered_at": at,
        }
        return self.worlds.append_event(
            tenant_id, world_id, event_id, "RESOURCE_POOL_REGISTERED",
            [
                {"op": "SET", "path": ["operations", "resource_pools", resource_id], "value": pool},
                self._clock_mutation(at),
            ],
            actor_id=actor_id, expected_version=expected_version,
            authorization_ref=authorization_ref, timestamp=at,
        )

    def create_goal(
        self,
        tenant_id: str,
        world_id: str,
        goal_id: str,
        description: str,
        *,
        event_id: str,
        actor_id: str,
        expected_version: int,
        authorization_ref: str,
        priority: int = 50,
        deadline: str | None = None,
        dependencies: Iterable[str] = (),
        parent_goal_id: str | None = None,
        owner_id: str | None = None,
        success_criteria: Iterable[str] = (),
        activate: bool = True,
        timestamp: str | None = None,
    ) -> dict[str, Any]:
        _, operations = self._snapshot(tenant_id, world_id)
        goal_id = _identifier(goal_id, "goal_id")
        if goal_id in operations["goals"]:
            raise OperationsError("goal is already registered")
        description = str(description).strip()
        if len(description) < 10 or len(description) > 10_000:
            raise OperationsError("goal description must contain between 10 and 10000 characters")
        priority = int(priority)
        if priority < 0 or priority > 100:
            raise OperationsError("goal priority must be between 0 and 100")
        dependency_ids = _string_set(dependencies, "goal dependency")
        missing = [item for item in dependency_ids if item not in operations["goals"]]
        if missing:
            raise OperationsError(f"goal dependencies are not registered: {', '.join(missing)}")
        if activate and any(
            operations["goals"].get(dependency, {}).get("status") != "COMPLETED"
            for dependency in dependency_ids
        ):
            raise OperationsError("active goal dependencies are not complete")
        parent = _identifier(parent_goal_id, "parent_goal_id") if parent_goal_id else None
        if parent and parent not in operations["goals"]:
            raise OperationsError("parent goal is not registered")
        owner = _identifier(owner_id, "owner_id") if owner_id else None
        if owner and owner not in operations["agents"]:
            raise OperationsError("goal owner is not a registered agent")
        at = _timestamp(timestamp or _now(), "timestamp")
        goal = {
            "goal_id": goal_id,
            "description": description,
            "status": "ACTIVE" if activate else "PROPOSED",
            "priority": priority,
            "deadline": _timestamp(deadline, "deadline") if deadline else None,
            "dependencies": dependency_ids,
            "parent_goal_id": parent,
            "owner_id": owner,
            "success_criteria": _string_set(success_criteria, "success criterion"),
            "active_plan_id": None,
            "created_at": at,
            "updated_at": at,
        }
        return self.worlds.append_event(
            tenant_id, world_id, event_id, "GOAL_CREATED",
            [
                {"op": "SET", "path": ["operations", "goals", goal_id], "value": goal},
                self._clock_mutation(at),
            ],
            actor_id=actor_id, expected_version=expected_version,
            authorization_ref=authorization_ref, timestamp=at,
        )

    def transition_goal(
        self,
        tenant_id: str,
        world_id: str,
        goal_id: str,
        status: str,
        *,
        event_id: str,
        actor_id: str,
        expected_version: int,
        authorization_ref: str,
        reason: str,
        timestamp: str | None = None,
    ) -> dict[str, Any]:
        _, operations = self._snapshot(tenant_id, world_id)
        goal_id = _identifier(goal_id, "goal_id")
        goal = deepcopy(operations["goals"].get(goal_id))
        if not goal:
            raise OperationsError("goal is not registered")
        status = str(status).upper()
        if status not in GOAL_STATUSES or status not in GOAL_TRANSITIONS[goal["status"]]:
            raise OperationsError(f"invalid goal transition: {goal['status']} -> {status}")
        reason = str(reason).strip()
        if len(reason) < 5:
            raise OperationsError("goal transition reason must be explicit")
        if status == "ACTIVE":
            incomplete = [
                dependency for dependency in goal["dependencies"]
                if operations["goals"].get(dependency, {}).get("status") != "COMPLETED"
            ]
            if incomplete:
                raise OperationsError("goal dependencies are not complete")
        at = _timestamp(timestamp or _now(), "timestamp")
        goal.update({"status": status, "updated_at": at, "transition_reason": reason})
        return self.worlds.append_event(
            tenant_id, world_id, event_id, "GOAL_STATUS_CHANGED",
            [
                {"op": "SET", "path": ["operations", "goals", goal_id], "value": goal},
                self._clock_mutation(at),
            ],
            actor_id=actor_id, expected_version=expected_version,
            authorization_ref=authorization_ref, timestamp=at,
        )

    def _normalize_steps(self, raw_steps: Iterable[dict[str, Any]]) -> tuple[dict[str, dict[str, Any]], list[str]]:
        steps: dict[str, dict[str, Any]] = {}
        for index, raw in enumerate(raw_steps):
            if not isinstance(raw, dict):
                raise OperationsError(f"plan step {index} must be an object")
            step_id = _identifier(raw.get("step_id", ""), "step_id")
            if step_id in steps:
                raise OperationsError(f"duplicate plan step: {step_id}")
            action = str(raw.get("action", "")).strip()
            if len(action) < 3 or len(action) > 10_000:
                raise OperationsError("step action must contain between 3 and 10000 characters")
            requests = {
                _identifier(resource_id, "resource_id"): _number(amount, "resource request", minimum=0.000001)
                for resource_id, amount in _json_object(raw.get("resource_requests", {}), "resource_requests").items()
            }
            command = _json_object(raw.get("command", {}), "command")
            if command:
                command["binding_authority"] = False
            steps[step_id] = {
                "step_id": step_id,
                "action": action,
                "dependencies": _string_set(raw.get("dependencies", []), "step dependency"),
                "required_capabilities": _string_set(raw.get("required_capabilities", []), "required capability"),
                "resource_requests": requests,
                "resource_allocation": {},
                "earliest_start": _timestamp(raw["earliest_start"], "earliest_start") if raw.get("earliest_start") else None,
                "deadline": _timestamp(raw["deadline"], "step deadline") if raw.get("deadline") else None,
                "expected_outcomes": _string_set(raw.get("expected_outcomes", []), "expected outcome"),
                "command": command,
                "status": "PENDING",
                "assigned_agent_id": None,
                "assigned_at": None,
                "started_at": None,
                "completed_at": None,
            }
        if not steps:
            raise OperationsError("a plan must contain at least one step")
        for step in steps.values():
            missing = [dependency for dependency in step["dependencies"] if dependency not in steps]
            if missing:
                raise OperationsError(f"step dependencies are not in the plan: {', '.join(missing)}")
            if step["step_id"] in step["dependencies"]:
                raise OperationsError("a plan step cannot depend on itself")
        return steps, _topological_order(steps)

    def _build_plan(
        self,
        operations: dict[str, Any],
        plan_id: str,
        goal_id: str,
        raw_steps: Iterable[dict[str, Any]],
        *,
        horizon_start: str,
        horizon_end: str | None,
        created_at: str,
        supersedes: str | None = None,
    ) -> dict[str, Any]:
        plan_id = _identifier(plan_id, "plan_id")
        if plan_id in operations["plans"]:
            raise OperationsError("plan is already registered")
        goal_id = _identifier(goal_id, "goal_id")
        goal = operations["goals"].get(goal_id)
        if not goal:
            raise OperationsError("plan goal is not registered")
        if goal["status"] not in {"ACTIVE", "BLOCKED"}:
            raise OperationsError("plan goal must be active or blocked")
        start = _timestamp(horizon_start, "horizon_start")
        end = _timestamp(horizon_end, "horizon_end") if horizon_end else None
        if end and datetime.fromisoformat(end) <= datetime.fromisoformat(start):
            raise OperationsError("horizon_end must be after horizon_start")
        steps, order = self._normalize_steps(raw_steps)
        for step in steps.values():
            if step["earliest_start"] and datetime.fromisoformat(step["earliest_start"]) < datetime.fromisoformat(start):
                raise OperationsError("step earliest_start precedes the plan horizon")
            if end and step["deadline"] and datetime.fromisoformat(step["deadline"]) > datetime.fromisoformat(end):
                raise OperationsError("step deadline exceeds the plan horizon")
        revision = 1
        if supersedes:
            previous = operations["plans"].get(supersedes)
            if not previous:
                raise OperationsError("superseded plan is not registered")
            if previous["goal_id"] != goal_id:
                raise OperationsError("a replacement plan must serve the same goal")
            revision = int(previous["revision"]) + 1
        return {
            "plan_id": plan_id,
            "goal_id": goal_id,
            "revision": revision,
            "status": "ACTIVE",
            "horizon_start": start,
            "horizon_end": end,
            "supersedes": supersedes,
            "step_order": order,
            "steps": steps,
            "created_at": created_at,
            "updated_at": created_at,
        }

    def create_plan(
        self,
        tenant_id: str,
        world_id: str,
        plan_id: str,
        goal_id: str,
        steps: Iterable[dict[str, Any]],
        *,
        horizon_start: str,
        horizon_end: str | None,
        event_id: str,
        actor_id: str,
        expected_version: int,
        authorization_ref: str,
        timestamp: str | None = None,
    ) -> dict[str, Any]:
        _, operations = self._snapshot(tenant_id, world_id)
        at = _timestamp(timestamp or _now(), "timestamp")
        plan = self._build_plan(
            operations, plan_id, goal_id, steps,
            horizon_start=horizon_start, horizon_end=horizon_end, created_at=at,
        )
        goal = deepcopy(operations["goals"][plan["goal_id"]])
        goal.update({"active_plan_id": plan["plan_id"], "status": "ACTIVE", "updated_at": at})
        return self.worlds.append_event(
            tenant_id, world_id, event_id, "PLAN_CREATED",
            [
                {"op": "SET", "path": ["operations", "plans", plan["plan_id"]], "value": plan},
                {"op": "SET", "path": ["operations", "goals", plan["goal_id"]], "value": goal},
                self._clock_mutation(at),
            ],
            actor_id=actor_id, expected_version=expected_version,
            authorization_ref=authorization_ref, timestamp=at,
        )

    def replan(
        self,
        tenant_id: str,
        world_id: str,
        old_plan_id: str,
        new_plan_id: str,
        steps: Iterable[dict[str, Any]],
        *,
        horizon_start: str,
        horizon_end: str | None,
        event_id: str,
        actor_id: str,
        expected_version: int,
        authorization_ref: str,
        reason: str,
        timestamp: str | None = None,
    ) -> dict[str, Any]:
        _, operations = self._snapshot(tenant_id, world_id)
        old_plan_id = _identifier(old_plan_id, "old_plan_id")
        old = deepcopy(operations["plans"].get(old_plan_id))
        if not old:
            raise OperationsError("old plan is not registered")
        if old["status"] not in {"ACTIVE", "PAUSED", "NEEDS_REPLAN"}:
            raise OperationsError("old plan cannot be superseded from its current status")
        if any(step["status"] in {"ASSIGNED", "RUNNING"} for step in old["steps"].values()):
            raise OperationsError("active tasks must be resolved before replanning")
        reason = str(reason).strip()
        if len(reason) < 5:
            raise OperationsError("replan reason must be explicit")
        at = _timestamp(timestamp or _now(), "timestamp")
        new = self._build_plan(
            operations, new_plan_id, old["goal_id"], steps,
            horizon_start=horizon_start, horizon_end=horizon_end,
            created_at=at, supersedes=old_plan_id,
        )
        old.update({"status": "SUPERSEDED", "updated_at": at, "superseded_by": new["plan_id"], "reason": reason})
        goal = deepcopy(operations["goals"][old["goal_id"]])
        goal.update({"active_plan_id": new["plan_id"], "status": "ACTIVE", "updated_at": at})
        return self.worlds.append_event(
            tenant_id, world_id, event_id, "PLAN_REPLACED",
            [
                {"op": "SET", "path": ["operations", "plans", old_plan_id], "value": old},
                {"op": "SET", "path": ["operations", "plans", new["plan_id"]], "value": new},
                {"op": "SET", "path": ["operations", "goals", old["goal_id"]], "value": goal},
                self._clock_mutation(at),
            ],
            actor_id=actor_id, expected_version=expected_version,
            authorization_ref=authorization_ref, timestamp=at,
        )

    def ready_steps(self, tenant_id: str, world_id: str, *, at: str | None = None) -> list[dict[str, Any]]:
        _, operations = self._snapshot(tenant_id, world_id)
        current = datetime.fromisoformat(_timestamp(at or _now(), "at"))
        ready: list[tuple[int, str, int, str, dict[str, Any]]] = []
        for plan_id, plan in operations["plans"].items():
            if plan["status"] != "ACTIVE":
                continue
            goal = operations["goals"].get(plan["goal_id"], {})
            if goal.get("status") != "ACTIVE":
                continue
            for order, step_id in enumerate(plan["step_order"]):
                step = plan["steps"][step_id]
                if step["status"] != "PENDING":
                    continue
                if any(plan["steps"][dependency]["status"] != "SUCCEEDED" for dependency in step["dependencies"]):
                    continue
                if step["earliest_start"] and datetime.fromisoformat(step["earliest_start"]) > current:
                    continue
                deadline = step["deadline"] or goal.get("deadline") or "9999-12-31T23:59:59+00:00"
                row = {
                    "plan_id": plan_id,
                    "goal_id": plan["goal_id"],
                    "step": deepcopy(step),
                    "goal_priority": goal.get("priority", 0),
                    "binding_authority": False,
                }
                ready.append((-int(goal.get("priority", 0)), deadline, order, plan_id, row))
        ready.sort(key=lambda item: item[:4])
        return [item[4] for item in ready]

    def allocate_step_resources(
        self,
        tenant_id: str,
        world_id: str,
        plan_id: str,
        step_id: str,
        *,
        event_id: str,
        actor_id: str,
        expected_version: int,
        authorization_ref: str,
        timestamp: str | None = None,
    ) -> dict[str, Any]:
        _, operations = self._snapshot(tenant_id, world_id)
        plan_id = _identifier(plan_id, "plan_id")
        step_id = _identifier(step_id, "step_id")
        plan = deepcopy(operations["plans"].get(plan_id))
        if not plan or step_id not in plan["steps"]:
            raise OperationsError("plan step is not registered")
        if plan["status"] != "ACTIVE":
            raise OperationsError("resources can only be allocated to an active plan")
        step = plan["steps"][step_id]
        if step["status"] != "PENDING" or step["resource_allocation"]:
            raise OperationsError("resources can only be allocated once to a pending step")
        if any(plan["steps"][dependency]["status"] != "SUCCEEDED" for dependency in step["dependencies"]):
            raise OperationsError("step dependencies are not complete")
        allocation_key = f"{plan_id}:{step_id}"
        pools = deepcopy(operations["resource_pools"])
        for resource_id, amount in step["resource_requests"].items():
            pool = pools.get(resource_id)
            if not pool:
                raise OperationsError(f"resource pool is not registered: {resource_id}")
            if float(pool["capacity"]) - float(pool["allocated"]) < float(amount):
                raise OperationsError(f"insufficient resource capacity: {resource_id}")
        mutations: list[dict[str, Any]] = []
        for resource_id, amount in step["resource_requests"].items():
            pool = pools[resource_id]
            pool["allocated"] = float(pool["allocated"]) + float(amount)
            pool["allocations"][allocation_key] = float(amount)
            mutations.append({"op": "SET", "path": ["operations", "resource_pools", resource_id], "value": pool})
        step["resource_allocation"] = dict(step["resource_requests"])
        plan["updated_at"] = _timestamp(timestamp or _now(), "timestamp")
        mutations.extend([
            {"op": "SET", "path": ["operations", "plans", plan_id], "value": plan},
            self._clock_mutation(plan["updated_at"]),
        ])
        return self.worlds.append_event(
            tenant_id, world_id, event_id, "RESOURCES_ALLOCATED",
            mutations, actor_id=actor_id, expected_version=expected_version,
            authorization_ref=authorization_ref, timestamp=plan["updated_at"],
        )

    def assign_step(
        self,
        tenant_id: str,
        world_id: str,
        plan_id: str,
        step_id: str,
        agent_id: str,
        *,
        event_id: str,
        actor_id: str,
        expected_version: int,
        authorization_ref: str,
        timestamp: str | None = None,
    ) -> dict[str, Any]:
        _, operations = self._snapshot(tenant_id, world_id)
        plan_id = _identifier(plan_id, "plan_id")
        step_id = _identifier(step_id, "step_id")
        agent_id = _identifier(agent_id, "agent_id")
        plan = deepcopy(operations["plans"].get(plan_id))
        agent = deepcopy(operations["agents"].get(agent_id))
        if not plan or step_id not in plan["steps"]:
            raise OperationsError("plan step is not registered")
        if not agent:
            raise OperationsError("agent is not registered")
        if plan["status"] != "ACTIVE":
            raise OperationsError("only active-plan steps can be assigned")
        step = plan["steps"][step_id]
        if step["status"] != "PENDING":
            raise OperationsError("only pending steps can be assigned")
        if any(plan["steps"][dependency]["status"] != "SUCCEEDED" for dependency in step["dependencies"]):
            raise OperationsError("step dependencies are not complete")
        if step["resource_requests"] != step["resource_allocation"]:
            raise OperationsError("step resources must be fully allocated before assignment")
        if agent["status"] not in {"AVAILABLE", "BUSY"}:
            raise OperationsError("agent is not available for assignment")
        if len(agent["active_tasks"]) >= int(agent["max_concurrent"]):
            raise OperationsError("agent concurrent-task capacity is exhausted")
        missing = sorted(set(step["required_capabilities"]) - set(agent["capabilities"]))
        if missing:
            raise OperationsError(f"agent lacks required capabilities: {', '.join(missing)}")
        at = _timestamp(timestamp or _now(), "timestamp")
        task_id = f"{plan_id}:{step_id}"
        step.update({"status": "ASSIGNED", "assigned_agent_id": agent_id, "assigned_at": at})
        agent["active_tasks"].append(task_id)
        agent["active_tasks"] = sorted(set(agent["active_tasks"]))
        agent["status"] = "BUSY" if len(agent["active_tasks"]) >= int(agent["max_concurrent"]) else "AVAILABLE"
        plan["updated_at"] = at
        return self.worlds.append_event(
            tenant_id, world_id, event_id, "STEP_ASSIGNED",
            [
                {"op": "SET", "path": ["operations", "plans", plan_id], "value": plan},
                {"op": "SET", "path": ["operations", "agents", agent_id], "value": agent},
                self._clock_mutation(at),
            ],
            actor_id=actor_id, expected_version=expected_version,
            authorization_ref=authorization_ref, timestamp=at,
        )

    def assignment_proposals(
        self,
        tenant_id: str,
        world_id: str,
        *,
        at: str | None = None,
    ) -> list[dict[str, Any]]:
        """Return deterministic, explicitly non-binding coordination proposals."""
        _, operations = self._snapshot(tenant_id, world_id)
        simulated_load = {
            agent_id: len(agent["active_tasks"])
            for agent_id, agent in operations["agents"].items()
        }
        proposals: list[dict[str, Any]] = []
        for ready in self.ready_steps(tenant_id, world_id, at=at):
            step = ready["step"]
            resource_feasible = all(
                resource_id in operations["resource_pools"]
                and float(operations["resource_pools"][resource_id]["capacity"])
                - float(operations["resource_pools"][resource_id]["allocated"]) >= float(amount)
                for resource_id, amount in step["resource_requests"].items()
            )
            selected: str | None = None
            for agent_id in sorted(operations["agents"]):
                agent = operations["agents"][agent_id]
                if agent["status"] not in {"AVAILABLE", "BUSY"}:
                    continue
                if simulated_load[agent_id] >= int(agent["max_concurrent"]):
                    continue
                if not set(step["required_capabilities"]).issubset(set(agent["capabilities"])):
                    continue
                selected = agent_id
                simulated_load[agent_id] += 1
                break
            proposal_identity = {
                "plan_id": ready["plan_id"],
                "step_id": step["step_id"],
                "agent_id": selected,
            }
            proposals.append({
                "proposal_id": "assignment:" + sha256_json(proposal_identity).split(":", 1)[1][:24],
                "plan_id": ready["plan_id"],
                "goal_id": ready["goal_id"],
                "step_id": step["step_id"],
                "recommended_agent_id": selected,
                "resource_feasible": resource_feasible,
                "dispatchable": selected is not None and resource_feasible,
                "binding_authority": False,
            })
        return proposals

    def dispatch_step(
        self,
        tenant_id: str,
        world_id: str,
        plan_id: str,
        step_id: str,
        agent_id: str,
        *,
        event_id: str,
        actor_id: str,
        expected_version: int,
        authorization_ref: str,
        timestamp: str | None = None,
    ) -> dict[str, Any]:
        """Atomically reserve resources and assign one ready step."""
        _, operations = self._snapshot(tenant_id, world_id)
        plan_id = _identifier(plan_id, "plan_id")
        step_id = _identifier(step_id, "step_id")
        agent_id = _identifier(agent_id, "agent_id")
        plan = deepcopy(operations["plans"].get(plan_id))
        agent = deepcopy(operations["agents"].get(agent_id))
        if not plan or step_id not in plan["steps"]:
            raise OperationsError("plan step is not registered")
        if not agent:
            raise OperationsError("agent is not registered")
        if plan["status"] != "ACTIVE":
            raise OperationsError("only active-plan steps can be dispatched")
        step = plan["steps"][step_id]
        if step["status"] != "PENDING" or step["resource_allocation"]:
            raise OperationsError("only unallocated pending steps can be dispatched")
        if any(plan["steps"][dependency]["status"] != "SUCCEEDED" for dependency in step["dependencies"]):
            raise OperationsError("step dependencies are not complete")
        if agent["status"] not in {"AVAILABLE", "BUSY"}:
            raise OperationsError("agent is not available for dispatch")
        if len(agent["active_tasks"]) >= int(agent["max_concurrent"]):
            raise OperationsError("agent concurrent-task capacity is exhausted")
        missing = sorted(set(step["required_capabilities"]) - set(agent["capabilities"]))
        if missing:
            raise OperationsError(f"agent lacks required capabilities: {', '.join(missing)}")
        pools = deepcopy(operations["resource_pools"])
        for resource_id, amount in step["resource_requests"].items():
            pool = pools.get(resource_id)
            if not pool:
                raise OperationsError(f"resource pool is not registered: {resource_id}")
            if float(pool["capacity"]) - float(pool["allocated"]) < float(amount):
                raise OperationsError(f"insufficient resource capacity: {resource_id}")
        at = _timestamp(timestamp or _now(), "timestamp")
        task_id = f"{plan_id}:{step_id}"
        mutations: list[dict[str, Any]] = []
        for resource_id, amount in step["resource_requests"].items():
            pool = pools[resource_id]
            pool["allocated"] = float(pool["allocated"]) + float(amount)
            pool["allocations"][task_id] = float(amount)
            mutations.append({"op": "SET", "path": ["operations", "resource_pools", resource_id], "value": pool})
        step.update({
            "resource_allocation": dict(step["resource_requests"]),
            "status": "ASSIGNED",
            "assigned_agent_id": agent_id,
            "assigned_at": at,
        })
        plan["updated_at"] = at
        agent["active_tasks"] = sorted(set(agent["active_tasks"] + [task_id]))
        agent["status"] = "BUSY" if len(agent["active_tasks"]) >= int(agent["max_concurrent"]) else "AVAILABLE"
        mutations.extend([
            {"op": "SET", "path": ["operations", "plans", plan_id], "value": plan},
            {"op": "SET", "path": ["operations", "agents", agent_id], "value": agent},
            self._clock_mutation(at),
        ])
        return self.worlds.append_event(
            tenant_id, world_id, event_id, "STEP_DISPATCHED",
            mutations, actor_id=actor_id, expected_version=expected_version,
            authorization_ref=authorization_ref, timestamp=at,
        )

    def start_step(
        self,
        tenant_id: str,
        world_id: str,
        plan_id: str,
        step_id: str,
        *,
        event_id: str,
        actor_id: str,
        expected_version: int,
        authorization_ref: str,
        timestamp: str | None = None,
    ) -> dict[str, Any]:
        _, operations = self._snapshot(tenant_id, world_id)
        plan_id = _identifier(plan_id, "plan_id")
        step_id = _identifier(step_id, "step_id")
        plan = deepcopy(operations["plans"].get(plan_id))
        if not plan or step_id not in plan["steps"]:
            raise OperationsError("plan step is not registered")
        step = plan["steps"][step_id]
        if step["status"] != "ASSIGNED":
            raise OperationsError("only assigned steps can start")
        at = _timestamp(timestamp or _now(), "timestamp")
        step.update({"status": "RUNNING", "started_at": at})
        plan["updated_at"] = at
        return self.worlds.append_event(
            tenant_id, world_id, event_id, "STEP_STARTED",
            [
                {"op": "SET", "path": ["operations", "plans", plan_id], "value": plan},
                self._clock_mutation(at),
            ],
            actor_id=actor_id, expected_version=expected_version,
            authorization_ref=authorization_ref, timestamp=at,
        )

    def record_step_outcome(
        self,
        tenant_id: str,
        world_id: str,
        plan_id: str,
        step_id: str,
        success: bool,
        summary: str,
        payload: dict[str, Any],
        *,
        event_id: str,
        outcome_id: str,
        actor_id: str,
        expected_version: int,
        authorization_ref: str,
        actual_outcomes: Iterable[str] = (),
        sensitivity: str = "INTERNAL",
        timestamp: str | None = None,
    ) -> dict[str, Any]:
        _, operations = self._snapshot(tenant_id, world_id)
        plan_id = _identifier(plan_id, "plan_id")
        step_id = _identifier(step_id, "step_id")
        outcome_id = _identifier(outcome_id, "outcome_id")
        if outcome_id in operations["outcomes"]:
            raise OperationsError("outcome is already registered")
        plan = deepcopy(operations["plans"].get(plan_id))
        if not plan or step_id not in plan["steps"]:
            raise OperationsError("plan step is not registered")
        step = plan["steps"][step_id]
        if step["status"] not in {"ASSIGNED", "RUNNING"}:
            raise OperationsError("only assigned or running steps can record an outcome")
        agent_id = step["assigned_agent_id"]
        agent = deepcopy(operations["agents"].get(agent_id))
        if not agent:
            raise OperationsError("assigned agent is missing")
        at = _timestamp(timestamp or _now(), "timestamp")
        actual = _string_set(actual_outcomes, "actual outcome")
        expected = set(step["expected_outcomes"])
        observed = set(actual)
        missing_expected = sorted(expected - observed)
        unexpected = sorted(observed - expected) if expected else []
        if not isinstance(success, bool):
            raise OperationsError("success must be a boolean")
        reported_success = success
        success = success and not missing_expected
        step.update({
            "status": "SUCCEEDED" if success else "FAILED",
            "completed_at": at,
            "actual_outcomes": actual,
        })
        allocation_key = f"{plan_id}:{step_id}"
        mutations: list[dict[str, Any]] = []
        for resource_id, amount in step["resource_allocation"].items():
            pool = deepcopy(operations["resource_pools"][resource_id])
            pool["allocated"] = max(0.0, float(pool["allocated"]) - float(amount))
            if not pool["renewable"]:
                pool["capacity"] = max(0.0, float(pool["capacity"]) - float(amount))
            pool["allocations"].pop(allocation_key, None)
            mutations.append({"op": "SET", "path": ["operations", "resource_pools", resource_id], "value": pool})
        task_id = allocation_key
        agent["active_tasks"] = [item for item in agent["active_tasks"] if item != task_id]
        if agent["status"] not in {"OFFLINE", "RETIRED"}:
            agent["status"] = "BUSY" if len(agent["active_tasks"]) >= int(agent["max_concurrent"]) else "AVAILABLE"
        outcome = {
            "outcome_id": outcome_id,
            "plan_id": plan_id,
            "step_id": step_id,
            "agent_id": agent_id,
            "success": success,
            "reported_success": reported_success,
            "summary": str(summary).strip(),
            "payload": _json_object(payload, "payload"),
            "actual_outcomes": actual,
            "missing_expected_outcomes": missing_expected,
            "unexpected_outcomes": unexpected,
            "recorded_at": at,
        }
        if len(outcome["summary"]) < 10:
            raise OperationsError("outcome summary must contain at least 10 characters")
        plan["updated_at"] = at
        goal = deepcopy(operations["goals"][plan["goal_id"]])
        alert: dict[str, Any] | None = None
        if success and all(candidate["status"] == "SUCCEEDED" for candidate in plan["steps"].values()):
            plan["status"] = "COMPLETED"
            goal.update({"status": "COMPLETED", "updated_at": at})
        elif not success:
            plan["status"] = "NEEDS_REPLAN"
            goal.update({"status": "BLOCKED", "updated_at": at})
            alert = {
                "alert_id": f"replan:{outcome_id}",
                "type": "REPLAN_REQUIRED",
                "severity": "HIGH",
                "plan_id": plan_id,
                "step_id": step_id,
                "reason": "step outcome failed",
                "created_at": at,
                "resolved": False,
            }
        learning = {
            "candidate_id": f"learning:{outcome_id}",
            "outcome_id": outcome_id,
            "mechanism": "STEP_OUTCOME",
            "training_eligible": False,
            "requires_authorized_review": True,
            "created_at": at,
        }
        mutations.extend([
            {"op": "SET", "path": ["operations", "plans", plan_id], "value": plan},
            {"op": "SET", "path": ["operations", "goals", plan["goal_id"]], "value": goal},
            {"op": "SET", "path": ["operations", "agents", agent_id], "value": agent},
            {"op": "SET", "path": ["operations", "outcomes", outcome_id], "value": outcome},
            {"op": "SET", "path": ["operations", "learning_candidates", learning["candidate_id"]], "value": learning},
        ])
        if alert:
            mutations.append({"op": "SET", "path": ["operations", "alerts", alert["alert_id"]], "value": alert})
        mutations.append(self._clock_mutation(at))
        snapshot = self.worlds.append_event(
            tenant_id, world_id, event_id, "STEP_OUTCOME_RECORDED",
            mutations, actor_id=actor_id, expected_version=expected_version,
            authorization_ref=authorization_ref, timestamp=at,
        )
        memory = self.memory.record_episode(
            tenant_id,
            outcome_id,
            world_id,
            "STEP_OUTCOME",
            outcome["summary"],
            outcome,
            occurred_at=at,
            sensitivity=sensitivity,
            actor_id=actor_id,
            authorization_ref=authorization_ref,
            source_event_ids=[event_id],
            provenance={
                "world_version": snapshot["version"],
                "world_state_sha256": snapshot["state_sha256"],
                "plan_id": plan_id,
                "step_id": step_id,
            },
            timestamp=at,
        )
        return {
            "outcome": outcome,
            "memory": memory,
            "learning_candidate": learning,
            "alert": alert,
            "world": snapshot,
            "binding_authority": False,
        }

    def cancel_step(
        self,
        tenant_id: str,
        world_id: str,
        plan_id: str,
        step_id: str,
        *,
        event_id: str,
        actor_id: str,
        expected_version: int,
        authorization_ref: str,
        reason: str,
        timestamp: str | None = None,
    ) -> dict[str, Any]:
        """Cancel a non-terminal step and release its agent and resource reservations."""
        _, operations = self._snapshot(tenant_id, world_id)
        plan_id = _identifier(plan_id, "plan_id")
        step_id = _identifier(step_id, "step_id")
        plan = deepcopy(operations["plans"].get(plan_id))
        if not plan or step_id not in plan["steps"]:
            raise OperationsError("plan step is not registered")
        step = plan["steps"][step_id]
        if step["status"] in {"SUCCEEDED", "FAILED", "CANCELLED"}:
            raise OperationsError("terminal step cannot be cancelled")
        reason = str(reason).strip()
        if len(reason) < 5:
            raise OperationsError("cancellation reason must be explicit")
        at = _timestamp(timestamp or _now(), "timestamp")
        task_id = f"{plan_id}:{step_id}"
        mutations: list[dict[str, Any]] = []
        for resource_id, amount in step["resource_allocation"].items():
            pool = deepcopy(operations["resource_pools"][resource_id])
            pool["allocated"] = max(0.0, float(pool["allocated"]) - float(amount))
            pool["allocations"].pop(task_id, None)
            mutations.append({"op": "SET", "path": ["operations", "resource_pools", resource_id], "value": pool})
        agent_id = step.get("assigned_agent_id")
        if agent_id:
            agent = deepcopy(operations["agents"].get(agent_id))
            if agent:
                agent["active_tasks"] = [item for item in agent["active_tasks"] if item != task_id]
                if agent["status"] not in {"OFFLINE", "RETIRED"}:
                    agent["status"] = "BUSY" if len(agent["active_tasks"]) >= int(agent["max_concurrent"]) else "AVAILABLE"
                mutations.append({"op": "SET", "path": ["operations", "agents", agent_id], "value": agent})
        step.update({
            "status": "CANCELLED",
            "completed_at": at,
            "cancellation_reason": reason,
            "resource_allocation": {},
        })
        plan.update({"status": "NEEDS_REPLAN", "updated_at": at})
        goal = deepcopy(operations["goals"][plan["goal_id"]])
        goal.update({"status": "BLOCKED", "updated_at": at})
        alert = {
            "alert_id": f"replan:cancel:{plan_id}:{step_id}",
            "type": "REPLAN_REQUIRED",
            "severity": "HIGH",
            "plan_id": plan_id,
            "step_id": step_id,
            "reason": reason,
            "created_at": at,
            "resolved": False,
        }
        mutations.extend([
            {"op": "SET", "path": ["operations", "plans", plan_id], "value": plan},
            {"op": "SET", "path": ["operations", "goals", plan["goal_id"]], "value": goal},
            {"op": "SET", "path": ["operations", "alerts", alert["alert_id"]], "value": alert},
            self._clock_mutation(at),
        ])
        snapshot = self.worlds.append_event(
            tenant_id, world_id, event_id, "STEP_CANCELLED",
            mutations, actor_id=actor_id, expected_version=expected_version,
            authorization_ref=authorization_ref, timestamp=at,
        )
        return {"alert": alert, "world": snapshot, "binding_authority": False}

    def monitor(self, tenant_id: str, world_id: str, *, at: str | None = None) -> list[dict[str, Any]]:
        _, operations = self._snapshot(tenant_id, world_id)
        current_text = _timestamp(at or _now(), "at")
        current = datetime.fromisoformat(current_text)
        alerts: list[dict[str, Any]] = []

        def add(kind: str, severity: str, subject: str, reason: str) -> None:
            fingerprint = sha256_json({"type": kind, "subject": subject, "reason": reason})
            alerts.append({
                "alert_id": "monitor:" + fingerprint.split(":", 1)[1][:24],
                "type": kind,
                "severity": severity,
                "subject": subject,
                "reason": reason,
                "observed_at": current_text,
                "resolved": False,
            })

        for goal_id, goal in operations["goals"].items():
            if goal["deadline"] and goal["status"] not in {"COMPLETED", "FAILED", "CANCELLED"}:
                if datetime.fromisoformat(goal["deadline"]) < current:
                    add("GOAL_OVERDUE", "HIGH", goal_id, "goal deadline has passed")
        for plan_id, plan in operations["plans"].items():
            if plan["status"] == "NEEDS_REPLAN":
                add("REPLAN_REQUIRED", "HIGH", plan_id, "plan is awaiting a corrective revision")
            for step_id, step in plan["steps"].items():
                if step["deadline"] and step["status"] not in {"SUCCEEDED", "FAILED", "CANCELLED"}:
                    if datetime.fromisoformat(step["deadline"]) < current:
                        add("STEP_OVERDUE", "HIGH", f"{plan_id}:{step_id}", "step deadline has passed")
                agent_id = step.get("assigned_agent_id")
                if agent_id and step["status"] in {"ASSIGNED", "RUNNING"}:
                    if operations["agents"].get(agent_id, {}).get("status") in {"OFFLINE", "RETIRED"}:
                        add("AGENT_UNAVAILABLE", "CRITICAL", f"{plan_id}:{step_id}", f"assigned agent {agent_id} is unavailable")
        for resource_id, pool in operations["resource_pools"].items():
            if float(pool["allocated"]) > float(pool["capacity"]):
                add("RESOURCE_OVERALLOCATED", "CRITICAL", resource_id, "allocated quantity exceeds capacity")
        alerts.sort(key=lambda row: (row["severity"], row["type"], row["subject"]))
        return alerts

    def record_monitoring_cycle(
        self,
        tenant_id: str,
        world_id: str,
        *,
        event_id: str,
        actor_id: str,
        expected_version: int,
        authorization_ref: str,
        at: str | None = None,
    ) -> dict[str, Any]:
        observed_at = _timestamp(at or _now(), "at")
        alerts = self.monitor(tenant_id, world_id, at=observed_at)
        mutations = [
            {"op": "SET", "path": ["operations", "alerts", alert["alert_id"]], "value": alert}
            for alert in alerts
        ]
        mutations.append(self._clock_mutation(observed_at))
        snapshot = self.worlds.append_event(
            tenant_id, world_id, event_id, "MONITORING_CYCLE_RECORDED",
            mutations, actor_id=actor_id, expected_version=expected_version,
            authorization_ref=authorization_ref, timestamp=observed_at,
        )
        return {"alerts": alerts, "world": snapshot, "binding_authority": False}