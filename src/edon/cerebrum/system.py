"""Non-authoritative Cerebrum System composition around the C1 model layer."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from edon.common.hashing import sha256_json
from edon.provenance import CausalProvenanceGraph

from .c1 import C1OperationsAdapter
from .state_engine import InstitutionalStateEngine


class CerebrumSystemError(RuntimeError):
    """Raised when a Cerebrum System cycle violates identity or boundary rules."""


_FORBIDDEN_TASK_CONTEXT_FIELDS = {
    "authorization_ref",
    "authorization_ref_sha256",
    "execution_token",
    "kernel_token",
    "commit_token",
    "binding_authority",
    "authorized",
    "executed",
}


def _forbidden_context_paths(value: Any, prefix: str = "task_context") -> list[str]:
    paths: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            path = f"{prefix}.{key}"
            if str(key).lower() in _FORBIDDEN_TASK_CONTEXT_FIELDS:
                paths.append(path)
            paths.extend(_forbidden_context_paths(child, path))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            paths.extend(_forbidden_context_paths(child, f"{prefix}[{index}]"))
    return paths


class CerebrumSystem:
    """Compose deterministic state/provenance services with non-binding C1 reasoning.

    Kernel authorization, commit, and external action delivery intentionally
    remain outside this class.
    """

    def __init__(
        self,
        tenant_id: str,
        world_id: str,
        c1_adapter: C1OperationsAdapter,
        *,
        state_engine: InstitutionalStateEngine | None = None,
        provenance: CausalProvenanceGraph | None = None,
    ):
        self.tenant_id = str(tenant_id).strip()
        self.world_id = str(world_id).strip()
        if not self.tenant_id or not self.world_id:
            raise CerebrumSystemError("tenant_id and world_id are required")
        self.c1 = c1_adapter
        self.state_engine = state_engine or InstitutionalStateEngine(
            self.tenant_id, self.world_id
        )
        self.provenance = provenance or CausalProvenanceGraph(
            self.tenant_id, self.world_id
        )
        if self.state_engine.tenant_id != self.tenant_id or self.state_engine.world_id != self.world_id:
            raise CerebrumSystemError("state engine identity does not match Cerebrum System")
        if self.provenance.tenant_id != self.tenant_id or self.provenance.world_id != self.world_id:
            raise CerebrumSystemError("provenance identity does not match Cerebrum System")

    def ingest_state_assertion(self, assertion: dict[str, Any]) -> dict[str, Any]:
        normalized = self.state_engine.ingest(assertion)
        self.provenance.record_node(
            f"state:{normalized['assertion_id']}",
            "STATE_ASSERTION",
            normalized["assertion_sha256"],
            occurred_at=normalized["occurred_at"],
            available_to_controller_at=normalized["available_to_controller_at"],
            metadata={
                "state_class": normalized["state_class"],
                "state_path": normalized["state_path"],
            },
        )
        return normalized

    def run_c1_cycle(
        self,
        cycle_id: str,
        *,
        decision_time: str,
        task_context: dict[str, Any],
    ) -> dict[str, Any]:
        normalized_cycle_id = str(cycle_id).strip()
        if not normalized_cycle_id:
            raise CerebrumSystemError("cycle_id is required")
        if not isinstance(task_context, dict):
            raise CerebrumSystemError("task_context must be an object")
        forbidden_paths = _forbidden_context_paths(task_context)
        if forbidden_paths:
            raise CerebrumSystemError(
                "task_context cannot carry execution authority: "
                + ", ".join(sorted(forbidden_paths))
            )
        projection = self.state_engine.project(decision_time)
        context = {
            **deepcopy(task_context),
            "schema_version": "edon-cerebrum-system-context.v1",
            "tenant_id": self.tenant_id,
            "world_id": self.world_id,
            "decision_time": projection["decision_time"],
            "institutional_state": projection,
            "task_context": deepcopy(task_context),
            "learned_component": "C1",
            "mode": "SHADOW",
            "binding_authority": False,
        }
        proposal = self.c1.propose(context)
        projection_node_id = f"projection:{projection['projection_sha256'].split(':', 1)[1][:24]}"
        proposal_node_id = f"c1:{normalized_cycle_id}"
        self.provenance.record_node(
            projection_node_id,
            "STATE_PROJECTION",
            projection["projection_sha256"],
            occurred_at=projection["decision_time"],
            available_to_controller_at=projection["decision_time"],
            metadata={"separated_state_classes": True},
        )
        self.provenance.record_node(
            proposal_node_id,
            "C1_INFERENCE",
            proposal["proposal_sha256"],
            occurred_at=projection["decision_time"],
            available_to_controller_at=projection["decision_time"],
            metadata={
                "model_lineage": proposal["model_lineage"],
                "proposal_type": proposal["proposal_type"],
            },
        )
        self.provenance.record_edge(
            f"edge:{normalized_cycle_id}:state-to-c1",
            projection_node_id,
            proposal_node_id,
            "INFORMED",
            evidence_status="DECLARED",
            evidence_refs=[projection["projection_sha256"], proposal["input_sha256"]],
            recorded_at=projection["decision_time"],
        )
        provenance = self.provenance.snapshot()
        core = {
            "schema_version": "edon-cerebrum-system-cycle.v1",
            "cycle_id": normalized_cycle_id,
            "tenant_id": self.tenant_id,
            "world_id": self.world_id,
            "decision_time": projection["decision_time"],
            "state_projection_sha256": projection["projection_sha256"],
            "context_sha256": sha256_json(context),
            "c1": {
                "architectural_name": "C1",
                "historical_component_name": "Cerebrum learned component",
                "model_lineage": proposal["model_lineage"],
            },
            "proposal": proposal,
            "provenance_graph_sha256": provenance["graph_sha256"],
            "kernel_authorization_requested": False,
            "executed": False,
            "binding_authority": False,
        }
        return {**core, "cycle_sha256": sha256_json(core)}


__all__ = ["CerebrumSystem", "CerebrumSystemError"]