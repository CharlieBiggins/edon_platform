"""Typed, non-authoritative C1 proposals for institutional operations.

Historical EDON experiments and compatibility interfaces called this learned
component Cerebrum.
"""

from __future__ import annotations

from typing import Any, Protocol

from edon.common.hashing import sha256_json


class OperationsProposalError(RuntimeError):
    """Raised when a model provider emits an unsafe or malformed operations proposal."""


class OperationsProvider(Protocol):
    def propose(self, context: dict[str, Any]) -> dict[str, Any]: ...


PROPOSAL_REQUIREMENTS = {
    "ABSTAIN": set(),
    "CREATE_GOAL": {"goal_id", "description"},
    "CREATE_PLAN": {"plan_id", "goal_id", "steps", "horizon_start"},
    "DISPATCH_STEP": {"plan_id", "step_id", "agent_id"},
    "REPLAN": {"old_plan_id", "new_plan_id", "steps", "horizon_start", "reason"},
    "CANCEL_STEP": {"plan_id", "step_id", "reason"},
}

FORBIDDEN_MODEL_FIELDS = {
    "authorization_ref", "execution_token", "kernel_token", "signature",
    "binding_eligible", "commit", "committed",
}


def _forbidden_paths(value: Any, prefix: str = "") -> list[str]:
    """Return nested model-output paths that attempt to carry authority."""

    found: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            path = f"{prefix}.{key}" if prefix else str(key)
            if key in FORBIDDEN_MODEL_FIELDS:
                found.append(path)
            if key == "binding_authority" and child is True:
                found.append(path)
            found.extend(_forbidden_paths(child, path))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            path = f"{prefix}[{index}]"
            found.extend(_forbidden_paths(child, path))
    return found


class OperationsProposalAdapter:
    """Validates provider output and preserves a hard proposal/authority firewall."""

    def __init__(self, provider: OperationsProvider, *, model_lineage: str):
        self.provider = provider
        self.model_lineage = str(model_lineage).strip()
        if not self.model_lineage:
            raise OperationsProposalError("model_lineage is required")

    def propose(self, context: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(context, dict):
            raise OperationsProposalError("operations context must be an object")
        raw = self.provider.propose(context)
        if not isinstance(raw, dict):
            raise OperationsProposalError("provider output must be an object")
        forbidden = sorted(set(_forbidden_paths(raw)))
        if forbidden:
            raise OperationsProposalError(
                "provider attempted to emit authority fields: " + ", ".join(forbidden)
            )
        if raw.get("binding_authority") not in {None, False}:
            raise OperationsProposalError("C1 proposal cannot carry binding authority")
        proposal_type = str(raw.get("proposal_type", "")).upper()
        if proposal_type not in PROPOSAL_REQUIREMENTS:
            raise OperationsProposalError(f"unsupported operations proposal: {proposal_type or '<missing>'}")
        payload = raw.get("payload", {})
        if not isinstance(payload, dict):
            raise OperationsProposalError("proposal payload must be an object")
        missing = sorted(PROPOSAL_REQUIREMENTS[proposal_type] - set(payload))
        if missing:
            raise OperationsProposalError("proposal payload is missing: " + ", ".join(missing))
        rationale = str(raw.get("rationale", "")).strip()
        if len(rationale) < 10 or len(rationale) > 10_000:
            raise OperationsProposalError("proposal rationale must contain between 10 and 10000 characters")
        confidence = raw.get("confidence")
        if isinstance(confidence, bool) or not isinstance(confidence, (int, float)):
            raise OperationsProposalError("proposal confidence must be numeric")
        confidence = float(confidence)
        if confidence < 0 or confidence > 1:
            raise OperationsProposalError("proposal confidence must be between 0 and 1")
        input_hash = sha256_json(context)
        proposal_core = {
            "schema_version": "edon-cerebrum-operations-proposal.v1",
            "proposal_id": str(raw.get("proposal_id") or "proposal:" + sha256_json(raw).split(":", 1)[1][:24]),
            "proposal_type": proposal_type,
            "payload": payload,
            "rationale": rationale,
            "confidence": confidence,
            "model_lineage": self.model_lineage,
            "input_sha256": input_hash,
            "binding_authority": False,
        }
        return {**proposal_core, "proposal_sha256": sha256_json(proposal_core)}


class DeterministicShadowProvider:
    """Reference provider that recommends the first feasible assignment or abstains."""

    def propose(self, context: dict[str, Any]) -> dict[str, Any]:
        assignments = context.get("assignment_proposals", [])
        for row in assignments if isinstance(assignments, list) else []:
            if row.get("dispatchable"):
                return {
                    "proposal_type": "DISPATCH_STEP",
                    "payload": {
                        "plan_id": row["plan_id"],
                        "step_id": row["step_id"],
                        "agent_id": row["recommended_agent_id"],
                    },
                    "rationale": "The step is ready, resources are feasible, and the agent has capacity.",
                    "confidence": 1.0,
                    "binding_authority": False,
                }
        return {
            "proposal_type": "ABSTAIN",
            "payload": {},
            "rationale": "No currently ready and feasible operational assignment was identified.",
            "confidence": 1.0,
            "binding_authority": False,
        }