"""One-cycle-at-a-time institutional shadow supervisor."""

from __future__ import annotations

from typing import Any

from edon.cerebrum.operations import OperationsProposalAdapter
from edon.common.hashing import sha256_json
from edon.operations import InstitutionalControlPlane

from .store import ShadowCycleStore


class ShadowSupervisor:
    """Builds context and records Cerebrum proposals without committing actions."""

    def __init__(
        self,
        control: InstitutionalControlPlane,
        adapter: OperationsProposalAdapter,
        cycles: ShadowCycleStore,
    ):
        self.control = control
        self.adapter = adapter
        self.cycles = cycles

    def run_cycle(
        self,
        tenant_id: str,
        world_id: str,
        cycle_id: str,
        *,
        at: str | None = None,
    ) -> dict[str, Any]:
        state = self.control.operational_state(tenant_id, world_id)
        context = {
            "schema_version": "edon-shadow-supervisor-context.v1",
            "tenant_id": tenant_id,
            "world_id": world_id,
            "world_version": state["world_version"],
            "world_state_sha256": state["world_state_sha256"],
            "operations": state["operations"],
            "alerts": self.control.monitor(tenant_id, world_id, at=at),
            "ready_steps": self.control.ready_steps(tenant_id, world_id, at=at),
            "assignment_proposals": self.control.assignment_proposals(
                tenant_id, world_id, at=at
            ),
            "mode": "SHADOW",
            "binding_authority": False,
        }
        proposal = self.adapter.propose(context)
        cycle = {
            "cycle_id": str(cycle_id),
            "tenant_id": tenant_id,
            "world_id": world_id,
            "world_version": state["world_version"],
            "world_state_sha256": state["world_state_sha256"],
            "context_sha256": sha256_json(context),
            "proposal": proposal,
            "executed": False,
            "binding_authority": False,
        }
        return self.cycles.record(cycle, timestamp=at)