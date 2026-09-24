"""Validated boundary between Cerebrum objectives and operations-research tools."""

from __future__ import annotations

import math
from copy import deepcopy
from typing import Any, Protocol

from edon.common.hashing import sha256_json


class OptimizationError(RuntimeError):
    """Raised when an optimization request or candidate violates its contract."""


FORBIDDEN_AUTHORITY_KEYS = {
    "authorization_ref", "execution_token", "kernel_token", "signature",
    "commit", "binding_authority", "approved", "authorized",
}


def _identifier(value: Any, label: str) -> str:
    normalized = str(value).strip()
    if not normalized or len(normalized) > 200:
        raise OptimizationError(f"{label} must contain between 1 and 200 characters")
    return normalized


def _quantity(value: Any, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise OptimizationError(f"{label} must be numeric")
    result = float(value)
    if not math.isfinite(result) or result < 0:
        raise OptimizationError(f"{label} must be finite and non-negative")
    return result


def _reject_authority(value: Any, path: str = "candidate") -> None:
    if isinstance(value, dict):
        for key, nested in value.items():
            if str(key).lower() in FORBIDDEN_AUTHORITY_KEYS:
                raise OptimizationError(f"optimization output cannot contain authority field {path}.{key}")
            _reject_authority(nested, f"{path}.{key}")
    elif isinstance(value, list):
        for index, nested in enumerate(value):
            _reject_authority(nested, f"{path}[{index}]")


class OptimizationProvider(Protocol):
    def solve(self, request: dict[str, Any]) -> dict[str, Any]: ...


class DeterministicCapacityAllocator:
    """Produces a stable feasible candidate; it makes no global-optimality claim."""

    def solve(self, request: dict[str, Any]) -> dict[str, Any]:
        supply_remaining = {
            row["supply_id"]: float(row["capacity"]) for row in request["supplies"]
        }
        lane_map: dict[str, list[dict[str, Any]]] = {}
        for lane in request["lanes"]:
            lane_map.setdefault(lane["demand_id"], []).append(lane)
        allocations: list[dict[str, Any]] = []
        unmet: dict[str, float] = {}
        demands = sorted(
            request["demands"], key=lambda row: (-int(row["priority"]), row["demand_id"])
        )
        for demand in demands:
            remaining = float(demand["quantity"])
            lanes = sorted(
                lane_map.get(demand["demand_id"], []),
                key=lambda row: (float(row["unit_cost"]), row["supply_id"]),
            )
            for lane in lanes:
                available = supply_remaining[lane["supply_id"]]
                amount = min(remaining, available, float(lane["max_quantity"]))
                if amount <= 0:
                    continue
                allocations.append(
                    {
                        "supply_id": lane["supply_id"],
                        "demand_id": demand["demand_id"],
                        "quantity": amount,
                        "unit_cost": float(lane["unit_cost"]),
                    }
                )
                supply_remaining[lane["supply_id"]] -= amount
                remaining -= amount
                if remaining <= 1e-12:
                    break
            if remaining > 1e-12:
                unmet[demand["demand_id"]] = remaining
        return {
            "allocations": allocations,
            "unmet_demand": unmet,
            "solver_status": "FEASIBLE" if not unmet else "PARTIAL",
            "optimality_claim": False,
        }


class OptimizationAdapter:
    """Normalizes requests and validates non-authoritative provider candidates."""

    def __init__(self, provider: OptimizationProvider, *, provider_lineage: str):
        self.provider = provider
        self.provider_lineage = _identifier(provider_lineage, "provider_lineage")

    @staticmethod
    def _normalize_request(request: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(request, dict):
            raise OptimizationError("optimization request must be a JSON object")
        objective = str(request.get("objective", "MINIMIZE_COST")).upper()
        if objective != "MINIMIZE_COST":
            raise OptimizationError("reference adapter supports MINIMIZE_COST only")
        supplies = []
        supply_ids: set[str] = set()
        for row in request.get("supplies", []):
            supply_id = _identifier(row["supply_id"], "supply_id")
            if supply_id in supply_ids:
                raise OptimizationError("duplicate supply_id")
            supply_ids.add(supply_id)
            supplies.append({"supply_id": supply_id, "capacity": _quantity(row["capacity"], "capacity")})
        demands = []
        demand_ids: set[str] = set()
        for row in request.get("demands", []):
            demand_id = _identifier(row["demand_id"], "demand_id")
            if demand_id in demand_ids:
                raise OptimizationError("duplicate demand_id")
            demand_ids.add(demand_id)
            priority = int(row.get("priority", 50))
            if not 0 <= priority <= 100:
                raise OptimizationError("priority must be between 0 and 100")
            demands.append(
                {"demand_id": demand_id, "quantity": _quantity(row["quantity"], "quantity"), "priority": priority}
            )
        if not supplies or not demands:
            raise OptimizationError("at least one supply and demand are required")
        supply_capacities = {row["supply_id"]: row["capacity"] for row in supplies}
        lanes = []
        lane_keys: set[tuple[str, str]] = set()
        for row in request.get("lanes", []):
            supply_id = _identifier(row["supply_id"], "lane supply_id")
            demand_id = _identifier(row["demand_id"], "lane demand_id")
            if supply_id not in supply_ids or demand_id not in demand_ids:
                raise OptimizationError("lane references an unknown supply or demand")
            key = (supply_id, demand_id)
            if key in lane_keys:
                raise OptimizationError("duplicate supply-demand lane")
            lane_keys.add(key)
            lanes.append(
                {
                    "supply_id": supply_id,
                    "demand_id": demand_id,
                    "unit_cost": _quantity(row["unit_cost"], "unit_cost"),
                    "max_quantity": _quantity(
                        row.get("max_quantity", supply_capacities[supply_id]), "max_quantity"
                    ),
                }
            )
        if not lanes:
            raise OptimizationError("at least one allocation lane is required")
        bindings = request.get("state_bindings", {})
        if not isinstance(bindings, dict):
            raise OptimizationError("state_bindings must be an object")
        normalized = {
            "schema_version": "edon-optimization-request.v1",
            "request_id": _identifier(request["request_id"], "request_id"),
            "tenant_id": _identifier(request["tenant_id"], "tenant_id"),
            "scope_id": _identifier(request["scope_id"], "scope_id"),
            "objective": objective,
            "supplies": sorted(supplies, key=lambda row: row["supply_id"]),
            "demands": sorted(demands, key=lambda row: row["demand_id"]),
            "lanes": sorted(lanes, key=lambda row: (row["supply_id"], row["demand_id"])),
            "require_full_demand": bool(request.get("require_full_demand", True)),
            "state_bindings": deepcopy(bindings),
        }
        return normalized

    @staticmethod
    def _validate_candidate(request: dict[str, Any], candidate: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(candidate, dict):
            raise OptimizationError("optimization provider must return an object")
        _reject_authority(candidate)
        supplies = {row["supply_id"]: row["capacity"] for row in request["supplies"]}
        demands = {row["demand_id"]: row["quantity"] for row in request["demands"]}
        lanes = {(row["supply_id"], row["demand_id"]): row for row in request["lanes"]}
        used_supply = {key: 0.0 for key in supplies}
        served_demand = {key: 0.0 for key in demands}
        used_lane = {key: 0.0 for key in lanes}
        allocations = []
        total_cost = 0.0
        for row in candidate.get("allocations", []):
            supply_id = _identifier(row["supply_id"], "candidate supply_id")
            demand_id = _identifier(row["demand_id"], "candidate demand_id")
            lane = lanes.get((supply_id, demand_id))
            if lane is None:
                raise OptimizationError("candidate uses an unregistered lane")
            quantity = _quantity(row["quantity"], "candidate quantity")
            if quantity > lane["max_quantity"] + 1e-9:
                raise OptimizationError("candidate exceeds lane capacity")
            supplied_cost = _quantity(row.get("unit_cost", lane["unit_cost"]), "candidate unit_cost")
            if abs(supplied_cost - lane["unit_cost"]) > 1e-9:
                raise OptimizationError("candidate changed a registered lane cost")
            used_supply[supply_id] += quantity
            served_demand[demand_id] += quantity
            used_lane[(supply_id, demand_id)] += quantity
            total_cost += quantity * lane["unit_cost"]
            allocations.append(
                {"supply_id": supply_id, "demand_id": demand_id, "quantity": quantity, "unit_cost": lane["unit_cost"]}
            )
        for supply_id, amount in used_supply.items():
            if amount > supplies[supply_id] + 1e-9:
                raise OptimizationError("candidate exceeds supply capacity")
        for demand_id, amount in served_demand.items():
            if amount > demands[demand_id] + 1e-9:
                raise OptimizationError("candidate overserves demand")
        for key, amount in used_lane.items():
            if amount > lanes[key]["max_quantity"] + 1e-9:
                raise OptimizationError("candidate exceeds cumulative lane capacity")
        unmet = {
            demand_id: max(0.0, demands[demand_id] - served_demand[demand_id])
            for demand_id in sorted(demands)
            if demands[demand_id] - served_demand[demand_id] > 1e-9
        }
        feasible = not unmet
        if request["require_full_demand"] and not feasible:
            status = "INFEASIBLE"
        else:
            status = "FEASIBLE" if feasible else "PARTIAL"
        return {
            "allocations": allocations,
            "unmet_demand": unmet,
            "total_cost": total_cost,
            "status": status,
            "feasible": feasible,
            "optimality_claim": False,
        }

    def propose(self, request: dict[str, Any]) -> dict[str, Any]:
        normalized = self._normalize_request(request)
        raw_candidate = self.provider.solve(deepcopy(normalized))
        candidate = self._validate_candidate(normalized, raw_candidate)
        envelope = {
            "schema_version": "edon-optimization-candidate.v1",
            "request_id": normalized["request_id"],
            "tenant_id": normalized["tenant_id"],
            "scope_id": normalized["scope_id"],
            "objective": normalized["objective"],
            "request_sha256": sha256_json(normalized),
            "provider_lineage": self.provider_lineage,
            **candidate,
            "binding_authority": False,
            "requires_kernel_authorization": True,
        }
        envelope["candidate_sha256"] = sha256_json(envelope)
        return envelope