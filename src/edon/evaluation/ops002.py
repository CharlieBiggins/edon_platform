"""EDON-OPS-002 governed closed-loop integration evaluation."""

from __future__ import annotations

import tempfile
from pathlib import Path

from edon.cerebrum import DeterministicShadowProvider, OperationsProposalAdapter
from edon.kernel import KernelAuthorizedWorld, KernelTokenAuthority, KernelTokenError
from edon.memory import EpisodicMemoryStore
from edon.operations import InstitutionalControlPlane
from edon.outbox import TransactionalOutbox
from edon.supervisor import ShadowCycleStore, ShadowSupervisor
from edon.world import WorldStateStore


def run_ops002() -> dict:
    """Run a deterministic internal evaluation and return its gate report."""
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        worlds = WorldStateStore(root / "world.sqlite3")
        memory = EpisodicMemoryStore(root / "memory.sqlite3")
        control = InstitutionalControlPlane(worlds, memory)
        control.bootstrap_world(
            "tenant-eval", "institution", {"name": "OPS-002 institution"},
            actor_id="kernel", authorization_ref="bootstrap",
            timestamp="2026-08-21T04:00:00+00:00",
        )
        control.register_agent(
            "tenant-eval", "institution", "agent-capable", "SOFTWARE",
            ["inspect", "report"], event_id="agent-capable", actor_id="kernel",
            expected_version=0, authorization_ref="agent-auth",
            timestamp="2026-08-21T04:01:00+00:00",
        )
        control.register_agent(
            "tenant-eval", "institution", "agent-ineligible", "SOFTWARE",
            ["archive"], event_id="agent-ineligible", actor_id="kernel",
            expected_version=1, authorization_ref="agent-auth-2",
            timestamp="2026-08-21T04:02:00+00:00",
        )
        control.register_resource_pool(
            "tenant-eval", "institution", "compute", 2, "unit",
            event_id="resource", actor_id="kernel", expected_version=2,
            authorization_ref="resource-auth",
            timestamp="2026-08-21T04:03:00+00:00",
        )
        control.create_goal(
            "tenant-eval", "institution", "goal-inspection",
            "Inspect the operational anomaly and deliver a verified report.",
            event_id="goal", actor_id="kernel", expected_version=3,
            authorization_ref="goal-auth", priority=90,
            timestamp="2026-08-21T04:04:00+00:00",
        )
        control.create_plan(
            "tenant-eval", "institution", "plan-v1", "goal-inspection",
            [{
                "step_id": "inspect",
                "action": "Inspect the registered operational anomaly.",
                "required_capabilities": ["inspect"],
                "resource_requests": {"compute": 1},
                "expected_outcomes": ["inspection verified"],
            }],
            horizon_start="2026-08-21T04:00:00+00:00", horizon_end=None,
            event_id="plan", actor_id="kernel", expected_version=4,
            authorization_ref="plan-auth", timestamp="2026-08-21T04:05:00+00:00",
        )
        version_before_shadow = worlds.get_world("tenant-eval", "institution")["version"]
        adapter = OperationsProposalAdapter(
            DeterministicShadowProvider(), model_lineage="ops002-reference:v1"
        )
        supervisor = ShadowSupervisor(
            control, adapter, ShadowCycleStore(root / "cycles.sqlite3")
        )
        cycle = supervisor.run_cycle(
            "tenant-eval", "institution", "cycle-001", at="2026-08-21T04:06:00+00:00"
        )
        version_after_shadow = worlds.get_world("tenant-eval", "institution")["version"]
        assignment = cycle["proposal"]["payload"]
        dispatched = control.dispatch_step(
            "tenant-eval", "institution", assignment["plan_id"], assignment["step_id"],
            assignment["agent_id"], event_id="dispatch", actor_id="kernel",
            expected_version=5, authorization_ref="dispatch-auth",
            timestamp="2026-08-21T04:07:00+00:00",
        )
        control.start_step(
            "tenant-eval", "institution", "plan-v1", "inspect",
            event_id="start", actor_id="kernel", expected_version=6,
            authorization_ref="start-auth", timestamp="2026-08-21T04:08:00+00:00",
        )
        outcome = control.record_step_outcome(
            "tenant-eval", "institution", "plan-v1", "inspect", True,
            "The agent reported success but did not provide the expected verification.",
            {"reported": "complete"}, event_id="outcome", outcome_id="outcome-001",
            actor_id="kernel", expected_version=7, authorization_ref="outcome-auth",
            actual_outcomes=[], timestamp="2026-08-21T04:09:00+00:00",
        )
        replanned = control.replan(
            "tenant-eval", "institution", "plan-v1", "plan-v2",
            [{
                "step_id": "inspect-again",
                "action": "Repeat inspection with explicit verification evidence.",
                "required_capabilities": ["inspect"],
                "resource_requests": {"compute": 1},
                "expected_outcomes": ["inspection verified"],
            }],
            horizon_start="2026-08-21T04:10:00+00:00", horizon_end=None,
            event_id="replan", actor_id="kernel", expected_version=8,
            authorization_ref="replan-auth", reason="Verification evidence was missing.",
            timestamp="2026-08-21T04:10:00+00:00",
        )

        outbox = TransactionalOutbox(worlds.path)
        pending = outbox.claim("ops002-worker", limit=100, now="2026-08-21T04:11:00+00:00")
        for message in pending:
            outbox.acknowledge(
                message["message_id"], "ops002-worker", now="2026-08-21T04:11:01+00:00"
            )

        token_worlds = WorldStateStore(root / "token-world.sqlite3")
        authority = KernelTokenAuthority(root / "token-ledger.sqlite3", b"o" * 32)
        secured = KernelAuthorizedWorld(token_worlds, authority)
        initial = {"status": "READY"}
        token = authority.issue_world_event(
            tenant_id="tenant-eval", world_id="token-world", actor_id="kernel",
            authority_version="authority:v1", expected_world_version=-1,
            event_id="WORLD_CREATED", event_type="WORLD_CREATED",
            mutations=[{"op": "REPLACE_ROOT", "path": [], "value": initial}],
        )
        secured.create_world(
            "tenant-eval", "token-world", initial, actor_id="kernel",
            authority_version="authority:v1", execution_token=token,
        )
        replay_rejected = False
        try:
            authority.verify_world_event(
                token, tenant_id="tenant-eval", world_id="token-world", actor_id="kernel",
                authority_version="authority:v1", expected_world_version=-1,
                event_id="DIFFERENT", event_type="WORLD_CREATED",
                mutations=[{"op": "REPLACE_ROOT", "path": [], "value": initial}],
            )
        except KernelTokenError:
            replay_rejected = True

        final_operations = replanned["state"]["operations"]
        gates = {
            "shadow_cycle_non_binding": version_before_shadow == version_after_shadow,
            "deterministic_capability_assignment": assignment.get("agent_id") == "agent-capable",
            "atomic_resource_dispatch": (
                dispatched["state"]["operations"]["resource_pools"]["compute"]["allocated"] == 1
            ),
            "missing_expected_outcome_forces_failure": (
                outcome["outcome"]["reported_success"] is True
                and outcome["outcome"]["success"] is False
            ),
            "failed_outcome_requires_replan": outcome["alert"]["type"] == "REPLAN_REQUIRED",
            "learning_candidate_not_training_eligible": (
                outcome["learning_candidate"]["training_eligible"] is False
            ),
            "additive_plan_revision": (
                final_operations["plans"]["plan-v1"]["status"] == "SUPERSEDED"
                and final_operations["plans"]["plan-v2"]["revision"] == 2
            ),
            "world_event_replay_valid": worlds.verify_world("tenant-eval", "institution")["passed"],
            "transactional_outbox_delivered": (
                len(outbox.list_messages(status="PENDING")) == 0
                and len(outbox.list_messages(status="DELIVERED")) == len(pending)
            ),
            "kernel_token_request_binding": replay_rejected,
        }
        return {
            "schema_version": "edon-ops-002-evaluation.v1",
            "evaluation_id": "EDON-OPS-002",
            "status": "PASS" if all(gates.values()) else "FAIL",
            "gates": gates,
            "checks_passed": sum(gates.values()),
            "check_count": len(gates),
            "binding_authority": False,
            "claim_scope": "Internal deterministic integration evidence only",
        }