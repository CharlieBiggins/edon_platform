"""EDON-FED-001 hierarchical coordination and solver-boundary evaluation."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

from edon.federation import FederationError, InstitutionalFederationStore
from edon.memory import EpisodicMemoryStore
from edon.operations import InstitutionalControlPlane
from edon.optimization import (
    DeterministicCapacityAllocator,
    OptimizationAdapter,
    OptimizationError,
)
from edon.world import WorldStateStore


class _AuthoritySmugglingProvider:
    def solve(self, request: dict) -> dict:
        return {"allocations": [], "binding_authority": True}


def run_fed001() -> dict:
    """Run the bounded internal hierarchical deployment evaluation."""
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        worlds = WorldStateStore(root / "worlds.sqlite3")
        memory = EpisodicMemoryStore(root / "memory.sqlite3")
        operations = InstitutionalControlPlane(worlds, memory)
        for world_id, capacity in (("hub-memphis", 7), ("hub-indianapolis", 5)):
            operations.bootstrap_world(
                "tenant-logistics", world_id, {"name": world_id},
                actor_id="kernel", authorization_ref=f"bootstrap-{world_id}",
                timestamp="2026-08-22T01:00:00+00:00",
            )
            operations.register_resource_pool(
                "tenant-logistics", world_id, "sort-capacity", capacity, "volume-unit",
                event_id=f"resource-{world_id}", actor_id="kernel", expected_version=0,
                authorization_ref=f"resource-auth-{world_id}",
                timestamp="2026-08-22T01:01:00+00:00",
            )
        operations.ingest_observation(
            "tenant-logistics", "hub-memphis", "weather-001", "TELEMETRY",
            "weather-feed", "Restricted raw storm forecast for Memphis operations.",
            {"raw_secret": "do-not-federate", "storm_probability": 0.91},
            observed_at="2026-08-22T01:02:00+00:00", confidence=0.91,
            sensitivity="RESTRICTED", event_id="weather-event", actor_id="kernel",
            expected_version=1, authorization_ref="weather-auth",
            timestamp="2026-08-22T01:02:00+00:00",
        )

        federation = InstitutionalFederationStore(root / "federation.sqlite3", worlds)
        scopes = (
            ("global", "GLOBAL", None, None),
            ("ground", "DOMAIN", "global", None),
            ("east", "REGION", "ground", None),
            ("memphis", "FACILITY", "east", "hub-memphis"),
            ("indianapolis", "FACILITY", "east", "hub-indianapolis"),
        )
        for scope_id, scope_type, parent, world_id in scopes:
            federation.register_scope(
                "tenant-logistics", scope_id, scope_type, scope_id.title(),
                parent_scope_id=parent, world_id=world_id,
                created_at="2026-08-22T01:03:00+00:00",
            )
        memphis_projection = federation.project_world(
            "tenant-logistics", "memphis", "projection-memphis",
            created_at="2026-08-22T01:04:00+00:00",
        )
        federation.project_world(
            "tenant-logistics", "indianapolis", "projection-indianapolis",
            created_at="2026-08-22T01:04:00+00:00",
        )
        region_projection = federation.aggregate_scope(
            "tenant-logistics", "east", "projection-east",
            ["memphis", "indianapolis"], publish_to_scope_id="ground",
            created_at="2026-08-22T01:05:00+00:00",
        )
        federation.aggregate_scope(
            "tenant-logistics", "ground", "projection-ground", ["east"],
            publish_to_scope_id="global", created_at="2026-08-22T01:06:00+00:00",
        )
        global_projection = federation.aggregate_scope(
            "tenant-logistics", "global", "projection-global", ["ground"],
            created_at="2026-08-22T01:07:00+00:00",
        )

        local_route = federation.route_decision(
            "tenant-logistics", "decision-local", "memphis", [], impact_score=0.10,
            uncertainty=0.10, context={"action": "open-sort-line"},
            created_at="2026-08-22T01:08:00+00:00",
        )
        cross_route = federation.route_decision(
            "tenant-logistics", "decision-cross-hub", "memphis", ["indianapolis"],
            impact_score=0.20, uncertainty=0.10,
            context={"action": "move-volume", "quantity": 3}, severity="HIGH",
            evidence_sha256=[memphis_projection["summary_sha256"]],
            created_at="2026-08-22T01:09:00+00:00",
        )
        federation.record_escalation_event(
            "tenant-logistics", cross_route["escalation"]["escalation_id"],
            "ACKNOWLEDGED", "regional-operator", "Regional review started.",
            created_at="2026-08-22T01:10:00+00:00",
        )
        federation.record_escalation_event(
            "tenant-logistics", cross_route["escalation"]["escalation_id"],
            "RESOLVED", "regional-operator", "Candidate forwarded for Kernel review.",
            created_at="2026-08-22T01:11:00+00:00",
        )
        authority_route = federation.route_decision(
            "tenant-logistics", "decision-global-authority", "memphis", ["indianapolis"],
            impact_score=0.80, uncertainty=0.05,
            required_authority_scope_id="global", context={"action": "network-rebalance"},
            severity="CRITICAL", created_at="2026-08-22T01:12:00+00:00",
        )

        request = {
            "request_id": "allocation-001",
            "tenant_id": "tenant-logistics",
            "scope_id": "east",
            "objective": "MINIMIZE_COST",
            "supplies": [
                {"supply_id": "memphis", "capacity": 7},
                {"supply_id": "indianapolis", "capacity": 5},
            ],
            "demands": [
                {"demand_id": "critical", "quantity": 6, "priority": 100},
                {"demand_id": "standard", "quantity": 5, "priority": 50},
            ],
            "lanes": [
                {"supply_id": "memphis", "demand_id": "critical", "unit_cost": 1},
                {"supply_id": "indianapolis", "demand_id": "critical", "unit_cost": 2},
                {"supply_id": "memphis", "demand_id": "standard", "unit_cost": 3},
                {"supply_id": "indianapolis", "demand_id": "standard", "unit_cost": 1},
            ],
            "state_bindings": {"projection_sha256": region_projection["summary_sha256"]},
        }
        candidate = OptimizationAdapter(
            DeterministicCapacityAllocator(), provider_lineage="capacity-reference:v1"
        ).propose(request)
        smuggling_rejected = False
        try:
            OptimizationAdapter(
                _AuthoritySmugglingProvider(), provider_lineage="adversarial-provider:v1"
            ).propose(request)
        except OptimizationError:
            smuggling_rejected = True
        tenant_isolation = False
        try:
            federation.least_common_ancestor("different-tenant", ["memphis", "indianapolis"])
        except FederationError:
            tenant_isolation = True

        raw_projection_text = json.dumps(memphis_projection, sort_keys=True)
        escalations = federation.list_escalations("tenant-logistics", "east")
        global_resource = global_projection["summary"]["resources"]["sort-capacity"]
        served = {"critical": 0.0, "standard": 0.0}
        for allocation in candidate["allocations"]:
            served[allocation["demand_id"]] += allocation["quantity"]
        gates = {
            "hierarchy_has_single_root": federation.least_common_ancestor(
                "tenant-logistics", ["memphis", "indianapolis"]
            ) == "east",
            "world_projection_is_redacted": (
                memphis_projection["summary"]["contains_raw_records"] is False
                and "do-not-federate" not in raw_projection_text
            ),
            "projection_is_world_version_bound": (
                memphis_projection["summary"]["source_world_version"] == 2
                and bool(memphis_projection["summary"]["source_state_sha256"])
            ),
            "multilevel_aggregate_preserves_capacity": (
                global_resource["capacity"] == 12.0 and global_resource["allocated"] == 0.0
            ),
            "local_decision_stays_local": (
                local_route["disposition"] == "HANDLE_LOCAL"
                and local_route["target_scope_id"] == "memphis"
            ),
            "cross_scope_decision_uses_lca": (
                cross_route["disposition"] == "ESCALATE"
                and cross_route["target_scope_id"] == "east"
            ),
            "higher_authority_routes_to_global": authority_route["target_scope_id"] == "global",
            "escalation_lifecycle_is_additive": (
                len(escalations) == 1 and escalations[0]["status"] == "RESOLVED"
                and [event["event_type"] for event in escalations[0]["events"]]
                == ["OPENED", "ACKNOWLEDGED", "RESOLVED"]
            ),
            "tenant_scope_isolation": tenant_isolation,
            "optimization_candidate_respects_constraints": (
                candidate["status"] == "FEASIBLE"
                and served == {"critical": 6.0, "standard": 5.0}
            ),
            "optimization_candidate_is_non_binding": (
                candidate["binding_authority"] is False
                and candidate["requires_kernel_authorization"] is True
                and candidate["optimality_claim"] is False
            ),
            "optimization_authority_smuggling_rejected": smuggling_rejected,
        }
        return {
            "schema_version": "edon-fed-001-evaluation.v1",
            "evaluation_id": "EDON-FED-001",
            "status": "PASS" if all(gates.values()) else "FAIL",
            "gates": gates,
            "checks_passed": sum(gates.values()),
            "check_count": len(gates),
            "binding_authority": False,
            "claim_scope": "Internal deterministic hierarchical-coordination evidence only",
        }