"""Authenticated standard-library API for the integrated EDON MVP."""

from __future__ import annotations

import hashlib
import hmac
import json
import secrets
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from edon.actionnet import (
    ActionNetPlatformStore,
    CounterfactualEngine,
    GovernedAbstractionValidator,
    GovernedLearningNetwork,
    HumanBehaviorEngine,
    MechanismCompositionEngine,
    ProceduralInstitutionGenerator,
    generate_actionnet,
)
from edon.common.hashing import sha256_json
from edon.compiler import compile_institution
from edon.federation import InstitutionalFederationStore
from edon.gateway import AgentGateway, AgentGatewayStore
from edon.gaps import discover_gaps
from edon.memory import EpisodicMemoryStore
from edon.kernel import KernelAuthorizedWorld, KernelTokenAuthority
from edon.operations import InstitutionalControlPlane
from edon.optimization import DeterministicCapacityAllocator, OptimizationAdapter
from edon.outbox import TransactionalOutbox
from edon.qualification import qualify_actionnet
from edon.registry import ReviewRegistry
from edon.runtime import InstitutionalRuntime
from edon.shadow import run_shadow_comparison
from edon.world import WorldStateStore
from edon.cerebrum import (
    C1OperationsAdapter,
    OperationsProvider,
    configured_operations_provider,
)
from edon.supervisor import ShadowCycleStore, ShadowSupervisor

from .dashboard import DASHBOARD_HTML


ROLE_PERMISSIONS = {
    "VIEWER": {"read"},
    "COMPILER_OPERATOR": {"read", "compile", "simulate", "generate"},
    "REVIEWER": {"read", "review"},
    "DOMAIN_REVIEWER": {"read", "review"},
    "SAFETY_REVIEWER": {"read", "review"},
    "EXECUTIVE_RISK_OWNER": {"read", "review"},
    "RELEASE_MANAGER": {"read", "promote", "rollback"},
    "SHADOW_OPERATOR": {"read", "shadow", "gaps"},
    "KERNEL_AUTHORIZER": {"read", "authorize"},
    "KERNEL_COMMITTER": {"read", "kernel_commit"},
    "FEDERATION_OPERATOR": {"read", "federation", "optimize"},
    "OPTIMIZATION_OPERATOR": {"read", "optimize"},
    "GATEWAY_ADMIN": {"read", "gateway_read", "gateway_admin"},
    "GATEWAY_OPERATOR": {"read", "gateway_read", "gateway_ingest", "gateway_egress"},
    "GATEWAY_INGRESS": {"read", "gateway_ingest"},
    "ACTIONNET_AUTHOR": {"read", "actionnet_read", "actionnet_author"},
    "ACTIONNET_DOMAIN_REVIEWER": {"read", "actionnet_read", "actionnet_review"},
    "ACTIONNET_SAFETY_REVIEWER": {"read", "actionnet_read", "actionnet_review"},
    "ACTIONNET_PRIVACY_REVIEWER": {"read", "actionnet_read", "actionnet_review"},
    "ACTIONNET_CUSTODIAN": {
        "read", "actionnet_read", "actionnet_custody", "actionnet_author"
    },
    "ACTIONNET_RELEASE_MANAGER": {
        "read", "actionnet_read", "actionnet_review", "actionnet_release"
    },
    "ACTIONNET_CURRICULUM_OPERATOR": {
        "read", "actionnet_read", "actionnet_curriculum"
    },
    "ACTIONNET_INTERVENTION_OPERATOR": {
        "read", "actionnet_read", "actionnet_intervention"
    },
    "ACTIONNET_INTAKE_OPERATOR": {
        "read", "actionnet_read", "actionnet_intake"
    },
    "ACTIONNET_GLOBAL_CUSTODIAN": {
        "read", "actionnet_read", "actionnet_global"
    },
    "C1_RELEASE_MANAGER": {"read", "actionnet_read", "c1_release"},
    "WORLD_OPERATOR": {"read", "world", "memory", "operations"},
    "OPERATIONS_OPERATOR": {"read", "world", "memory", "operations"},
    "ADMIN": {
        "read", "compile", "simulate", "generate", "review", "promote", "rollback",
        "shadow", "gaps", "world", "memory", "operations", "authorize", "kernel_commit",
        "federation", "optimize",
        "gateway_read", "gateway_admin", "gateway_ingest", "gateway_egress",
        "actionnet_read", "actionnet_author", "actionnet_review",
        "actionnet_custody", "actionnet_release", "actionnet_curriculum",
        "actionnet_intervention", "actionnet_intake",
        "actionnet_global", "c1_release",
    },
}

ROLE_MEMORY_SENSITIVITIES = {
    "WORLD_OPERATOR": {"PUBLIC", "INTERNAL", "CONFIDENTIAL"},
    "OPERATIONS_OPERATOR": {"PUBLIC", "INTERNAL", "CONFIDENTIAL"},
    "ADMIN": {"PUBLIC", "INTERNAL", "CONFIDENTIAL", "RESTRICTED"},
}


def authorized(role: str, permission: str) -> bool:
    return permission in ROLE_PERMISSIONS.get(role, set())


class PlatformService:
    def __init__(
        self,
        state_dir: Path | str,
        *,
        operations_provider: OperationsProvider | None = None,
        model_lineage: str | None = None,
        c1_provider: OperationsProvider | None = None,
        c1_model_lineage: str | None = None,
    ):
        self.state_dir = Path(state_dir)
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.state_dir.chmod(0o700)
        self.registry = ReviewRegistry(self.state_dir / "registry.sqlite3")
        self.runtime = InstitutionalRuntime()
        self.worlds = WorldStateStore(self.state_dir / "world-state.sqlite3")
        self.memory = EpisodicMemoryStore(self.state_dir / "episodic-memory.sqlite3")
        self.operations = InstitutionalControlPlane(self.worlds, self.memory)
        self.actionnet_product = ActionNetPlatformStore(
            self.state_dir / "actionnet-platform.sqlite3"
        )
        self.learning_network = GovernedLearningNetwork(
            self.state_dir / "actionnet-learning-network.sqlite3",
            self.actionnet_product,
        )
        self.actionnet_world_generator = ProceduralInstitutionGenerator()
        self.actionnet_composition_engine = MechanismCompositionEngine()
        self.actionnet_counterfactual_engine = CounterfactualEngine()
        self.actionnet_behavior_engine = HumanBehaviorEngine()
        self.actionnet_intake_validator = GovernedAbstractionValidator()
        key_path = self.state_dir / "kernel-signing.key"
        if key_path.exists():
            signing_secret = key_path.read_bytes()
        else:
            signing_secret = secrets.token_bytes(32)
            key_path.write_bytes(signing_secret)
            key_path.chmod(0o600)
        self.kernel_authority = KernelTokenAuthority(
            self.state_dir / "kernel-tokens.sqlite3", signing_secret
        )
        self.kernel_worlds = KernelAuthorizedWorld(self.worlds, self.kernel_authority)
        self.outbox = TransactionalOutbox(self.worlds.path)
        self.federation = InstitutionalFederationStore(
            self.state_dir / "federation.sqlite3", self.worlds
        )
        self.agent_gateway = AgentGateway(
            AgentGatewayStore(self.state_dir / "agent-gateway.sqlite3")
        )
        self.optimization = OptimizationAdapter(
            DeterministicCapacityAllocator(), provider_lineage="capacity-reference:v1"
        )
        if operations_provider is not None and c1_provider is not None:
            raise ValueError("provide c1_provider or historical operations_provider, not both")
        selected_provider = c1_provider or operations_provider
        selected_lineage = c1_model_lineage or model_lineage
        if selected_provider is None:
            selected_provider, configured_lineage = configured_operations_provider()
            selected_lineage = selected_lineage or configured_lineage
        if not selected_lineage:
            raise ValueError("model_lineage is required for an injected operations provider")
        self.c1_provider = selected_provider
        self.c1_model_lineage = str(selected_lineage)
        # Compatibility aliases preserve historical integrations and experiment language.
        self.cerebrum_provider = self.c1_provider
        self.cerebrum_model_lineage = self.c1_model_lineage
        self.shadow_cycles = ShadowCycleStore(self.state_dir / "shadow-cycles.sqlite3")
        self.shadow_supervisor = ShadowSupervisor(
            self.operations,
            C1OperationsAdapter(
                self.c1_provider, model_lineage=self.c1_model_lineage
            ),
            self.shadow_cycles,
        )

    def _write_artifact(self, category: str, payload: dict[str, Any]) -> dict[str, str]:
        digest = sha256_json(payload)
        directory = self.state_dir / "artifacts" / category
        directory.mkdir(parents=True, exist_ok=True)
        protected = category == "actionnet-protected"
        directory.chmod(0o700 if protected else 0o755)
        path = directory / f"{digest.split(':', 1)[1]}.json"
        path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        path.chmod(0o600 if protected else 0o644)
        return {"sha256": digest, "path": str(path.relative_to(self.state_dir))}

    def compile(self, bundle: dict[str, Any]) -> dict[str, Any]:
        run_id = str(bundle.get("compiler_run_id", ""))
        if not run_id or any(character not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_" for character in run_id):
            raise ValueError("compiler_run_id must use letters, digits, hyphens, or underscores")
        input_dir = self.state_dir / "compiler-inputs"
        input_dir.mkdir(parents=True, exist_ok=True)
        input_dir.chmod(0o700)
        path = input_dir / f"{run_id}.json"
        path.write_text(json.dumps(bundle, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        path.chmod(0o600)
        report = compile_institution(path)
        candidate_ids = self.registry.register_compiler_run(report)
        artifact = self._write_artifact("compiler-runs", report)
        return {"compiler_run_id": run_id, "candidate_ids": candidate_ids, "artifact": artifact, "report": report}

    def review(self, body: dict[str, Any]) -> dict[str, Any]:
        return self.registry.submit_review(
            str(body["candidate_id"]),
            str(body["reviewer_id"]),
            str(body["reviewer_role"]),
            str(body["decision"]),
            str(body["rationale"]),
            resolutions=dict(body.get("resolutions", {})),
        )

    def promote(self, body: dict[str, Any]) -> dict[str, Any]:
        mechanism = self.registry.promote(str(body["candidate_id"]), str(body["promoter_id"]))
        return {"mechanism": mechanism, "artifact": self._write_artifact("mechanisms", mechanism)}

    def rollback(self, body: dict[str, Any]) -> dict[str, Any]:
        mechanism = self.registry.rollback(
            str(body["mechanism_id"]),
            str(body["target_version"]),
            str(body["actor_id"]),
            str(body["rationale"]),
        )
        return {"mechanism": mechanism}

    def simulate(self, body: dict[str, Any]) -> dict[str, Any]:
        mechanism = self.registry.get_mechanism(str(body["mechanism_id"]), body.get("version"))
        if "events" in body:
            return self.runtime.execute_events(mechanism, dict(body["initial_state"]), list(body["events"]))
        return self.runtime.evaluate(mechanism, dict(body["state"])).as_dict()

    def actionnet(self, body: dict[str, Any]) -> dict[str, Any]:
        mechanism = self.registry.get_mechanism(str(body["mechanism_id"]), body.get("version"))
        bundle = generate_actionnet(mechanism, generator_seed=int(body.get("generator_seed", 0)))
        qualification = qualify_actionnet(mechanism, bundle)
        public_artifact = self._write_artifact("actionnet-public", bundle["public"])
        protected_artifact = self._write_artifact("actionnet-protected", bundle["protected"])
        return {
            "manifest": bundle["manifest"],
            "qualification": qualification,
            "public_artifact": public_artifact,
            "protected_artifact": protected_artifact,
            "binding_authority": False,
        }

    def shadow(self, body: dict[str, Any]) -> dict[str, Any]:
        report = run_shadow_comparison(list(body.get("records", [])))
        return {"report": report, "artifact": self._write_artifact("shadow", report)}

    def gaps(self, body: dict[str, Any]) -> dict[str, Any]:
        shadow_report = body.get("shadow_report")
        if not isinstance(shadow_report, dict):
            shadow_report = run_shadow_comparison(list(body.get("records", [])))
        report = discover_gaps(shadow_report, minimum_repetitions=int(body.get("minimum_repetitions", 2)))
        return {"report": report, "artifact": self._write_artifact("gaps", report)}

    def create_world(self, body: dict[str, Any]) -> dict[str, Any]:
        return self.worlds.create_world(
            str(body["tenant_id"]),
            str(body["world_id"]),
            dict(body["initial_state"]),
            actor_id=str(body["actor_id"]),
            authorization_ref=str(body["authorization_ref"]),
            source_lineage=list(body.get("source_lineage", [])),
        )

    def append_world_event(self, body: dict[str, Any]) -> dict[str, Any]:
        return self.worlds.append_event(
            str(body["tenant_id"]),
            str(body["world_id"]),
            str(body["event_id"]),
            str(body["event_type"]),
            list(body["mutations"]),
            actor_id=str(body["actor_id"]),
            expected_version=int(body["expected_version"]),
            authorization_ref=str(body["authorization_ref"]),
            source_lineage=list(body.get("source_lineage", [])),
        )

    def restore_world(self, body: dict[str, Any]) -> dict[str, Any]:
        return self.worlds.restore_version(
            str(body["tenant_id"]),
            str(body["world_id"]),
            int(body["target_version"]),
            event_id=str(body["event_id"]),
            actor_id=str(body["actor_id"]),
            expected_version=int(body["expected_version"]),
            authorization_ref=str(body["authorization_ref"]),
        )

    def world_state(self, body: dict[str, Any]) -> dict[str, Any]:
        if "version" in body:
            return self.worlds.state_at(
                str(body["tenant_id"]), str(body["world_id"]), int(body["version"])
            )
        return self.worlds.get_world(str(body["tenant_id"]), str(body["world_id"]))

    def world_history(self, body: dict[str, Any]) -> dict[str, Any]:
        return {
            "items": self.worlds.events(str(body["tenant_id"]), str(body["world_id"])),
            "binding_authority": False,
        }

    def verify_world(self, body: dict[str, Any]) -> dict[str, Any]:
        return self.worlds.verify_world(str(body["tenant_id"]), str(body["world_id"]))

    def record_memory(self, body: dict[str, Any]) -> dict[str, Any]:
        return self.memory.record_episode(
            str(body["tenant_id"]),
            str(body["memory_id"]),
            str(body["world_id"]),
            str(body["episode_type"]),
            str(body["summary"]),
            dict(body["payload"]),
            occurred_at=str(body["occurred_at"]),
            sensitivity=str(body["sensitivity"]),
            actor_id=str(body["actor_id"]),
            authorization_ref=str(body["authorization_ref"]),
            source_event_ids=list(body.get("source_event_ids", [])),
            provenance=dict(body.get("provenance", {})),
            retention_until=body.get("retention_until"),
        )

    def query_memory(self, body: dict[str, Any]) -> dict[str, Any]:
        return {
            "items": self.memory.query(
                str(body["tenant_id"]),
                str(body.get("query", "")),
                actor_id=str(body["actor_id"]),
                allowed_sensitivities=list(body["allowed_sensitivities"]),
                world_id=body.get("world_id"),
                episode_types=list(body.get("episode_types", [])),
                limit=int(body.get("limit", 20)),
                as_of=body.get("as_of"),
            ),
            "binding_authority": False,
        }

    def tombstone_memory(self, body: dict[str, Any]) -> dict[str, Any]:
        return self.memory.tombstone(
            str(body["tenant_id"]),
            str(body["memory_id"]),
            actor_id=str(body["actor_id"]),
            reason=str(body["reason"]),
            authorization_ref=str(body["authorization_ref"]),
        )

    def bootstrap_operations(self, body: dict[str, Any]) -> dict[str, Any]:
        return self.operations.bootstrap_world(
            str(body["tenant_id"]),
            str(body["world_id"]),
            dict(body["institution"]),
            actor_id=str(body["actor_id"]),
            authorization_ref=str(body["authorization_ref"]),
            source_lineage=list(body.get("source_lineage", [])),
        )

    def initialize_operations(self, body: dict[str, Any]) -> dict[str, Any]:
        return self.operations.initialize_existing_world(
            str(body["tenant_id"]), str(body["world_id"]),
            event_id=str(body["event_id"]), actor_id=str(body["actor_id"]),
            expected_version=int(body["expected_version"]),
            authorization_ref=str(body["authorization_ref"]),
        )

    def operational_state(self, body: dict[str, Any]) -> dict[str, Any]:
        return self.operations.operational_state(str(body["tenant_id"]), str(body["world_id"]))

    def ingest_observation(self, body: dict[str, Any]) -> dict[str, Any]:
        return self.operations.ingest_observation(
            str(body["tenant_id"]), str(body["world_id"]),
            str(body["observation_id"]), str(body["modality"]), str(body["source_id"]),
            str(body["summary"]), dict(body["payload"]),
            observed_at=str(body["observed_at"]), confidence=float(body["confidence"]),
            sensitivity=str(body["sensitivity"]), event_id=str(body["event_id"]),
            actor_id=str(body["actor_id"]), expected_version=int(body["expected_version"]),
            authorization_ref=str(body["authorization_ref"]),
            provenance=dict(body.get("provenance", {})),
            retention_until=body.get("retention_until"),
        )

    def register_agent(self, body: dict[str, Any]) -> dict[str, Any]:
        return self.operations.register_agent(
            str(body["tenant_id"]), str(body["world_id"]), str(body["agent_id"]),
            str(body["kind"]), list(body.get("capabilities", [])),
            event_id=str(body["event_id"]), actor_id=str(body["actor_id"]),
            expected_version=int(body["expected_version"]),
            authorization_ref=str(body["authorization_ref"]),
            max_concurrent=int(body.get("max_concurrent", 1)),
            relationships=dict(body.get("relationships", {})), metadata=dict(body.get("metadata", {})),
        )

    def set_agent_status(self, body: dict[str, Any]) -> dict[str, Any]:
        return self.operations.set_agent_status(
            str(body["tenant_id"]), str(body["world_id"]), str(body["agent_id"]),
            str(body["status"]), event_id=str(body["event_id"]),
            actor_id=str(body["actor_id"]), expected_version=int(body["expected_version"]),
            authorization_ref=str(body["authorization_ref"]),
        )

    def register_resource(self, body: dict[str, Any]) -> dict[str, Any]:
        return self.operations.register_resource_pool(
            str(body["tenant_id"]), str(body["world_id"]), str(body["resource_id"]),
            float(body["capacity"]), str(body["unit"]), event_id=str(body["event_id"]),
            actor_id=str(body["actor_id"]), expected_version=int(body["expected_version"]),
            authorization_ref=str(body["authorization_ref"]),
            renewable=bool(body.get("renewable", True)),
        )

    def create_goal(self, body: dict[str, Any]) -> dict[str, Any]:
        return self.operations.create_goal(
            str(body["tenant_id"]), str(body["world_id"]), str(body["goal_id"]),
            str(body["description"]), event_id=str(body["event_id"]),
            actor_id=str(body["actor_id"]), expected_version=int(body["expected_version"]),
            authorization_ref=str(body["authorization_ref"]), priority=int(body.get("priority", 50)),
            deadline=body.get("deadline"), dependencies=list(body.get("dependencies", [])),
            parent_goal_id=body.get("parent_goal_id"), owner_id=body.get("owner_id"),
            success_criteria=list(body.get("success_criteria", [])),
            activate=bool(body.get("activate", True)),
        )

    def transition_goal(self, body: dict[str, Any]) -> dict[str, Any]:
        return self.operations.transition_goal(
            str(body["tenant_id"]), str(body["world_id"]), str(body["goal_id"]),
            str(body["status"]), event_id=str(body["event_id"]),
            actor_id=str(body["actor_id"]), expected_version=int(body["expected_version"]),
            authorization_ref=str(body["authorization_ref"]), reason=str(body["reason"]),
        )

    def create_plan(self, body: dict[str, Any]) -> dict[str, Any]:
        return self.operations.create_plan(
            str(body["tenant_id"]), str(body["world_id"]), str(body["plan_id"]),
            str(body["goal_id"]), list(body["steps"]), horizon_start=str(body["horizon_start"]),
            horizon_end=body.get("horizon_end"), event_id=str(body["event_id"]),
            actor_id=str(body["actor_id"]), expected_version=int(body["expected_version"]),
            authorization_ref=str(body["authorization_ref"]),
        )

    def replan(self, body: dict[str, Any]) -> dict[str, Any]:
        return self.operations.replan(
            str(body["tenant_id"]), str(body["world_id"]), str(body["old_plan_id"]),
            str(body["new_plan_id"]), list(body["steps"]), horizon_start=str(body["horizon_start"]),
            horizon_end=body.get("horizon_end"), event_id=str(body["event_id"]),
            actor_id=str(body["actor_id"]), expected_version=int(body["expected_version"]),
            authorization_ref=str(body["authorization_ref"]), reason=str(body["reason"]),
        )

    def ready_steps(self, body: dict[str, Any]) -> dict[str, Any]:
        return {
            "items": self.operations.ready_steps(
                str(body["tenant_id"]), str(body["world_id"]), at=body.get("at")
            ),
            "binding_authority": False,
        }

    def allocate_resources(self, body: dict[str, Any]) -> dict[str, Any]:
        return self.operations.allocate_step_resources(
            str(body["tenant_id"]), str(body["world_id"]), str(body["plan_id"]),
            str(body["step_id"]), event_id=str(body["event_id"]),
            actor_id=str(body["actor_id"]), expected_version=int(body["expected_version"]),
            authorization_ref=str(body["authorization_ref"]),
        )

    def assign_step(self, body: dict[str, Any]) -> dict[str, Any]:
        return self.operations.assign_step(
            str(body["tenant_id"]), str(body["world_id"]), str(body["plan_id"]),
            str(body["step_id"]), str(body["agent_id"]), event_id=str(body["event_id"]),
            actor_id=str(body["actor_id"]), expected_version=int(body["expected_version"]),
            authorization_ref=str(body["authorization_ref"]),
        )

    def assignment_proposals(self, body: dict[str, Any]) -> dict[str, Any]:
        return {
            "items": self.operations.assignment_proposals(
                str(body["tenant_id"]), str(body["world_id"]), at=body.get("at")
            ),
            "binding_authority": False,
        }

    def dispatch_step(self, body: dict[str, Any]) -> dict[str, Any]:
        return self.operations.dispatch_step(
            str(body["tenant_id"]), str(body["world_id"]), str(body["plan_id"]),
            str(body["step_id"]), str(body["agent_id"]), event_id=str(body["event_id"]),
            actor_id=str(body["actor_id"]), expected_version=int(body["expected_version"]),
            authorization_ref=str(body["authorization_ref"]),
        )

    def start_step(self, body: dict[str, Any]) -> dict[str, Any]:
        return self.operations.start_step(
            str(body["tenant_id"]), str(body["world_id"]), str(body["plan_id"]),
            str(body["step_id"]), event_id=str(body["event_id"]),
            actor_id=str(body["actor_id"]), expected_version=int(body["expected_version"]),
            authorization_ref=str(body["authorization_ref"]),
        )

    def record_outcome(self, body: dict[str, Any]) -> dict[str, Any]:
        return self.operations.record_step_outcome(
            str(body["tenant_id"]), str(body["world_id"]), str(body["plan_id"]),
            str(body["step_id"]), body["success"], str(body["summary"]),
            dict(body["payload"]), event_id=str(body["event_id"]),
            outcome_id=str(body["outcome_id"]), actor_id=str(body["actor_id"]),
            expected_version=int(body["expected_version"]),
            authorization_ref=str(body["authorization_ref"]),
            actual_outcomes=list(body.get("actual_outcomes", [])),
            sensitivity=str(body.get("sensitivity", "INTERNAL")),
        )

    def cancel_step(self, body: dict[str, Any]) -> dict[str, Any]:
        return self.operations.cancel_step(
            str(body["tenant_id"]), str(body["world_id"]), str(body["plan_id"]),
            str(body["step_id"]), event_id=str(body["event_id"]),
            actor_id=str(body["actor_id"]), expected_version=int(body["expected_version"]),
            authorization_ref=str(body["authorization_ref"]), reason=str(body["reason"]),
        )

    def monitor_operations(self, body: dict[str, Any]) -> dict[str, Any]:
        return {
            "items": self.operations.monitor(
                str(body["tenant_id"]), str(body["world_id"]), at=body.get("at")
            ),
            "binding_authority": False,
        }

    def record_monitoring_cycle(self, body: dict[str, Any]) -> dict[str, Any]:
        return self.operations.record_monitoring_cycle(
            str(body["tenant_id"]), str(body["world_id"]), event_id=str(body["event_id"]),
            actor_id=str(body["actor_id"]), expected_version=int(body["expected_version"]),
            authorization_ref=str(body["authorization_ref"]), at=body.get("at"),
        )

    def issue_kernel_token(self, body: dict[str, Any]) -> dict[str, Any]:
        token = self.kernel_authority.issue_world_event(
            tenant_id=str(body["tenant_id"]), world_id=str(body["world_id"]),
            actor_id=str(body["subject_actor_id"]),
            authority_version=str(body["authority_version"]),
            expected_world_version=int(body["expected_world_version"]),
            event_id=str(body["event_id"]), event_type=str(body["event_type"]),
            mutations=list(body["mutations"]), ttl_seconds=int(body.get("ttl_seconds", 300)),
            issuer_id=str(body["issuer_id"]),
        )
        claims = self.kernel_authority.decode_and_verify_signature(token)
        return {
            "execution_token": token,
            "claims": claims,
            "binding_authority": True,
        }

    def kernel_create_world(self, body: dict[str, Any]) -> dict[str, Any]:
        return self.kernel_worlds.create_world(
            str(body["tenant_id"]), str(body["world_id"]), dict(body["initial_state"]),
            actor_id=str(body["actor_id"]), authority_version=str(body["authority_version"]),
            execution_token=str(body["execution_token"]),
            source_lineage=list(body.get("source_lineage", [])),
        )

    def kernel_append_world_event(self, body: dict[str, Any]) -> dict[str, Any]:
        return self.kernel_worlds.append_event(
            str(body["tenant_id"]), str(body["world_id"]), str(body["event_id"]),
            str(body["event_type"]), list(body["mutations"]),
            actor_id=str(body["actor_id"]), authority_version=str(body["authority_version"]),
            expected_version=int(body["expected_version"]),
            execution_token=str(body["execution_token"]),
            source_lineage=list(body.get("source_lineage", [])),
        )

    def run_shadow_supervisor(self, body: dict[str, Any]) -> dict[str, Any]:
        return self.shadow_supervisor.run_cycle(
            str(body["tenant_id"]), str(body["world_id"]), str(body["cycle_id"]),
            at=body.get("at"),
        )

    def register_federation_scope(self, body: dict[str, Any]) -> dict[str, Any]:
        return self.federation.register_scope(
            str(body["tenant_id"]), str(body["scope_id"]), str(body["scope_type"]),
            str(body["name"]), parent_scope_id=body.get("parent_scope_id"),
            world_id=body.get("world_id"),
            authority_domain=str(body.get("authority_domain", "institutional-operations")),
            decision_latency_class=str(body.get("decision_latency_class", "MINUTES")),
            data_policy=dict(body.get("data_policy", {})),
        )

    def project_federation_scope(self, body: dict[str, Any]) -> dict[str, Any]:
        return self.federation.project_world(
            str(body["tenant_id"]), str(body["scope_id"]), str(body["projection_id"]),
            target_scope_id=body.get("target_scope_id"),
        )

    def aggregate_federation_scope(self, body: dict[str, Any]) -> dict[str, Any]:
        return self.federation.aggregate_scope(
            str(body["tenant_id"]), str(body["target_scope_id"]),
            str(body["projection_id"]), list(body["source_scope_ids"]),
            publish_to_scope_id=body.get("publish_to_scope_id"),
        )

    def route_federation_decision(self, body: dict[str, Any]) -> dict[str, Any]:
        return self.federation.route_decision(
            str(body["tenant_id"]), str(body["decision_id"]),
            str(body["source_scope_id"]), list(body.get("consequence_scope_ids", [])),
            impact_score=float(body["impact_score"]), uncertainty=float(body["uncertainty"]),
            context=dict(body["context"]),
            required_authority_scope_id=body.get("required_authority_scope_id"),
            local_impact_threshold=float(body.get("local_impact_threshold", 0.35)),
            local_uncertainty_threshold=float(body.get("local_uncertainty_threshold", 0.25)),
            escalation_id=body.get("escalation_id"),
            severity=str(body.get("severity", "MEDIUM")),
            reason=str(body.get("reason", "Decision exceeded local coordination boundary.")),
            evidence_sha256=list(body.get("evidence_sha256", [])),
        )

    def record_federation_escalation_event(self, body: dict[str, Any]) -> dict[str, Any]:
        return self.federation.record_escalation_event(
            str(body["tenant_id"]), str(body["escalation_id"]), str(body["event_type"]),
            str(body["actor_id"]), str(body["note"]),
        )

    def list_federation_escalations(self, body: dict[str, Any]) -> dict[str, Any]:
        return {
            "items": self.federation.list_escalations(
                str(body["tenant_id"]), body.get("target_scope_id")
            ),
            "binding_authority": False,
        }

    def gateway_register_connector(self, body: dict[str, Any]) -> dict[str, Any]:
        return self.agent_gateway.register_connector(body)

    def gateway_set_connector_status(self, body: dict[str, Any]) -> dict[str, Any]:
        return self.agent_gateway.set_connector_status(body)

    def gateway_ingest(self, body: dict[str, Any]) -> dict[str, Any]:
        return self.agent_gateway.ingest(body)

    def gateway_stage_egress(self, body: dict[str, Any]) -> dict[str, Any]:
        return self.agent_gateway.stage_egress(body)

    def gateway_list_connectors(self, body: dict[str, Any]) -> dict[str, Any]:
        return self.agent_gateway.list_connectors(body)

    def gateway_list_messages(self, body: dict[str, Any]) -> dict[str, Any]:
        return self.agent_gateway.list_messages(body)

    def gateway_audit(self, body: dict[str, Any]) -> dict[str, Any]:
        return self.agent_gateway.audit(body)

    def optimization_candidate(self, body: dict[str, Any]) -> dict[str, Any]:
        return self.optimization.propose(body)

    def actionnet_register_mechanism(self, body: dict[str, Any]) -> dict[str, Any]:
        return self.actionnet_product.register_mechanism(
            str(body["tenant_id"]), str(body["mechanism_id"]), str(body["version"]),
            str(body["title"]), str(body["description"]), dict(body["specification"]),
            domains=list(body.get("domains", [])),
            evidence_grade=str(body.get("evidence_grade", "UNVERIFIED")),
            source_lineage=list(body.get("source_lineage", [])),
            created_by=str(body["created_by"]),
        )

    @staticmethod
    def _actionnet_protected_role(body: dict[str, Any]) -> bool:
        return str(body.get("actor_role", "")).upper() in {"ACTIONNET_CUSTODIAN", "ADMIN"}

    def actionnet_register_institutional_ir(self, body: dict[str, Any]) -> dict[str, Any]:
        protected = bool(body.get("protected", False))
        if protected and not self._actionnet_protected_role(body):
            raise ValueError("only the ActionNet custodian may register protected Institutional IR")
        return self.actionnet_product.register_institutional_ir(
            str(body["tenant_id"]), str(body["institution_id"]), str(body["version"]),
            dict(body["institutional_ir"]), source_lineage=list(body.get("source_lineage", [])),
            protected=protected, created_by=str(body["created_by"]),
        )

    def actionnet_register_composition(self, body: dict[str, Any]) -> dict[str, Any]:
        return self.actionnet_product.register_composition_edge(
            str(body["tenant_id"]), str(body["edge_id"]),
            str(body["source_mechanism_id"]), str(body["source_version"]),
            str(body["target_mechanism_id"]), str(body["target_version"]),
            str(body["relation_type"]), conditions=dict(body.get("conditions", {})),
            evidence_grade=str(body.get("evidence_grade", "UNVERIFIED")),
            provenance=dict(body.get("provenance", {})),
            created_by=str(body["created_by"]),
        )

    def actionnet_generate_world(self, body: dict[str, Any]) -> dict[str, Any]:
        generated = self.actionnet_world_generator.generate(
            str(body["blueprint_id"]), dict(body["specification"]),
            seed=int(body["generator_seed"]), adversarial=bool(body.get("adversarial", False)),
        )
        return self.actionnet_product.register_world_blueprint(
            str(body["tenant_id"]), str(body["blueprint_id"]), str(body["version"]),
            generated, generator_seed=int(body["generator_seed"]),
            adversarial=bool(body.get("adversarial", False)),
            protected=bool(body.get("protected", False)),
            created_by=str(body["created_by"]),
        )

    def actionnet_execute_composition(self, body: dict[str, Any]) -> dict[str, Any]:
        tenant_id = str(body["tenant_id"])
        ir_record = self.actionnet_product.institutional_ir(
            tenant_id, str(body["institution_id"]), str(body["institution_version"])
        )
        protected = bool(ir_record["protected"])
        if protected and not self._actionnet_protected_role(body):
            raise ValueError("only the ActionNet custodian may execute protected compositions")
        mechanism_refs = list(body["mechanism_refs"])
        mechanisms = [
            self.actionnet_product.mechanism(
                tenant_id, str(reference["mechanism_id"]), str(reference["version"])
            )
            for reference in mechanism_refs
        ]
        edges = [
            self.actionnet_product.composition_edge(tenant_id, str(edge_id))
            for edge_id in body.get("edge_ids", [])
        ]
        run = self.actionnet_composition_engine.compose(
            str(body["run_id"]), ir_record["institutional_ir"], mechanisms, edges,
            seed=int(body.get("seed", 0)),
        )
        run_record = self.actionnet_product.record_composition_run(
            tenant_id, run, protected=protected, created_by=str(body["created_by"])
        )
        experience = self.actionnet_product.record_experience(
            tenant_id, str(body["experience_id"]), "SIMULATOR",
            ir_record["institution_type"], mechanism_refs,
            dict(run["trajectory"]), dict(run["causal_trace"]),
            evidence_grade="SYNTHETIC_VERIFIED",
            provenance={
                "composition_run_id": run["run_id"],
                "composition_run_sha256": run["run_sha256"],
                "institution_ir_sha256": ir_record["institutional_ir"]["ir_sha256"],
                "actionability": run["actionability"],
            },
            created_by=str(body["created_by"]), protected=protected,
        )
        return {
            "composition_run": run_record,
            "experience": experience,
            "binding_authority": False,
        }

    def actionnet_generate_counterfactuals(self, body: dict[str, Any]) -> dict[str, Any]:
        tenant_id = str(body["tenant_id"])
        parent = self.actionnet_product.experience_state(
            tenant_id, str(body["parent_experience_id"])
        )
        protected = bool(parent["protected"])
        if protected and not self._actionnet_protected_role(body):
            raise ValueError("only the ActionNet custodian may generate protected counterfactuals")
        batch = self.actionnet_counterfactual_engine.generate(
            str(body["batch_id"]), parent["experience_id"], parent["trajectory"],
            list(body["interventions"]),
        )
        child_ids = []
        children = []
        for branch in batch["branches"]:
            child_id = f"{batch['batch_id']}-{branch['branch_id']}"
            child = self.actionnet_product.record_experience(
                tenant_id, child_id, "SIMULATOR", parent["institution_type"],
                parent["mechanism_refs"], dict(branch["trajectory"]),
                {
                    "counterfactual_parent_id": parent["experience_id"],
                    "intervention": branch["intervention"],
                    "changed_paths": branch["changed_paths"],
                    "verification": branch["verification"],
                },
                evidence_grade="SYNTHETIC_VERIFIED",
                provenance={
                    "counterfactual_batch_id": batch["batch_id"],
                    "branch_sha256": branch["branch_sha256"],
                },
                created_by=str(body["created_by"]),
                counterfactual_parent_id=parent["experience_id"], protected=protected,
            )
            child_ids.append(child_id)
            children.append(child)
        batch_record = self.actionnet_product.record_counterfactual_batch(
            tenant_id, batch, child_ids, protected=protected,
            created_by=str(body["created_by"]),
        )
        return {
            "counterfactual_batch": batch_record,
            "experiences": children,
            "binding_authority": False,
        }

    def actionnet_generate_behavior_scenario(self, body: dict[str, Any]) -> dict[str, Any]:
        tenant_id = str(body["tenant_id"])
        ir_record = self.actionnet_product.institutional_ir(
            tenant_id, str(body["institution_id"]), str(body["institution_version"])
        )
        protected = bool(ir_record["protected"])
        if protected and not self._actionnet_protected_role(body):
            raise ValueError("only the ActionNet custodian may generate protected behavior scenarios")
        scenario = self.actionnet_behavior_engine.generate(
            ir_record["institutional_ir"], seed=int(body["seed"])
        )
        return self.actionnet_product.record_behavior_scenario(
            tenant_id, str(body["scenario_id"]), ir_record["institution_id"],
            ir_record["version"], scenario, protected=protected,
            created_by=str(body["created_by"]),
        )

    def actionnet_ingest_governed_abstraction(self, body: dict[str, Any]) -> dict[str, Any]:
        tenant_id = str(body["tenant_id"])
        abstraction = self.actionnet_intake_validator.normalize(dict(body["abstraction"]))
        ir_reference = abstraction["institution_ir_ref"]
        ir_record = self.actionnet_product.institutional_ir(
            tenant_id, ir_reference["institution_id"], ir_reference["version"]
        )
        if ir_record["protected"] and not self._actionnet_protected_role(body):
            raise ValueError("only the ActionNet custodian may intake against protected Institutional IR")
        experience_id = str(body["experience_id"])
        experience = self.actionnet_product.record_experience(
            tenant_id, experience_id, "REAL_GOVERNED_ABSTRACTION",
            ir_record["institution_type"], abstraction["mechanism_refs"],
            abstraction["trajectory"], abstraction["causal_trace"],
            evidence_grade="SOURCE_GROUNDED",
            provenance={
                **abstraction["provenance"],
                "intake_id": abstraction["intake_id"],
                "source_fingerprint": abstraction["source_fingerprint"],
                "raw_payload_stored": False,
                "institution_ir_sha256": ir_record["institutional_ir"]["ir_sha256"],
            },
            created_by=str(body["created_by"]), protected=bool(ir_record["protected"]),
        )
        intake = self.actionnet_product.record_governed_intake(
            tenant_id, abstraction, experience_id, created_by=str(body["created_by"])
        )
        return {"intake": intake, "experience": experience, "binding_authority": False}

    def actionnet_record_experience(self, body: dict[str, Any]) -> dict[str, Any]:
        return self.actionnet_product.record_experience(
            str(body["tenant_id"]), str(body["experience_id"]), str(body["source_type"]),
            str(body["institution_type"]), list(body["mechanism_refs"]),
            dict(body["trajectory"]), dict(body["causal_trace"]),
            evidence_grade=str(body.get("evidence_grade", "UNVERIFIED")),
            provenance=dict(body.get("provenance", {})), created_by=str(body["created_by"]),
            counterfactual_parent_id=body.get("counterfactual_parent_id"),
            failure_classification=body.get("failure_classification"),
            protected=bool(body.get("protected", False)),
        )

    def actionnet_review_experience(self, body: dict[str, Any]) -> dict[str, Any]:
        return self.actionnet_product.review_experience(
            str(body["tenant_id"]), str(body["review_id"]), str(body["experience_id"]),
            str(body["reviewer_id"]), str(body["reviewer_role"]),
            str(body["dimension"]), str(body["decision"]), str(body["rationale"]),
        )

    def actionnet_overlap_check(self, body: dict[str, Any]) -> dict[str, Any]:
        return self.actionnet_product.record_overlap_check(
            str(body["tenant_id"]), str(body["experience_id"]), bool(body["passed"]),
            dict(body["report"]), actor_id=str(body["actor_id"]),
        )

    def actionnet_training_eligibility(self, body: dict[str, Any]) -> dict[str, Any]:
        return self.actionnet_product.approve_training_eligibility(
            str(body["tenant_id"]), str(body["experience_id"]),
            release_manager_id=str(body["release_manager_id"]),
            rationale=str(body["rationale"]),
        )

    def actionnet_quarantine_experience(self, body: dict[str, Any]) -> dict[str, Any]:
        return self.actionnet_product.quarantine_experience(
            str(body["tenant_id"]), str(body["experience_id"]), str(body["reason"]),
            actor_id=str(body["actor_id"]),
        )

    def actionnet_record_exposure(self, body: dict[str, Any]) -> dict[str, Any]:
        return self.actionnet_product.record_model_exposure(
            str(body["tenant_id"]), str(body["exposure_id"]),
            str(body["experience_id"]), str(body["model_id"]), str(body["purpose"]),
            created_by=str(body["created_by"]),
            dataset_release_id=body.get("dataset_release_id"),
        )

    def actionnet_coverage(self, body: dict[str, Any]) -> dict[str, Any]:
        return self.actionnet_product.coverage_report(
            str(body["tenant_id"]),
            minimum_experiences=int(body.get("minimum_experiences", 3)),
            minimum_domains=int(body.get("minimum_domains", 2)),
        )

    def actionnet_freeze_coverage(self, body: dict[str, Any]) -> dict[str, Any]:
        return self.actionnet_product.freeze_coverage_snapshot(
            str(body["tenant_id"]), str(body["snapshot_id"]),
            created_by=str(body["created_by"]),
            minimum_experiences=int(body.get("minimum_experiences", 3)),
            minimum_domains=int(body.get("minimum_domains", 2)),
        )

    def actionnet_recommend_acquisition(self, body: dict[str, Any]) -> dict[str, Any]:
        return self.actionnet_product.recommend_acquisition(
            str(body["tenant_id"]), str(body["recommendation_id"]),
            created_by=str(body["created_by"]),
            minimum_experiences=int(body.get("minimum_experiences", 3)),
            minimum_domains=int(body.get("minimum_domains", 2)),
        )

    def actionnet_record_intervention(self, body: dict[str, Any]) -> dict[str, Any]:
        return self.actionnet_product.record_intervention_candidate(
            str(body["tenant_id"]), str(body["intervention_id"]), str(body["scope_id"]),
            list(body["source_experience_ids"]), dict(body["action"]),
            dict(body["objectives"]), dict(body["constraints"]),
            dict(body["predicted_outcomes"]), dict(body.get("verification", {})),
            float(body["confidence"]), created_by=str(body["created_by"]),
        )

    def actionnet_create_release(self, body: dict[str, Any]) -> dict[str, Any]:
        return self.actionnet_product.create_training_release(
            str(body["tenant_id"]), str(body["release_id"]),
            list(body["experience_ids"]), str(body["model_target"]),
            release_manager_id=str(body["release_manager_id"]),
        )

    def actionnet_promote_global(self, body: dict[str, Any]) -> dict[str, Any]:
        return self.learning_network.promote_local_experience(
            str(body["tenant_id"]),
            str(body["request_id"]),
            str(body["experience_id"]),
            str(body["global_record_id"]),
            dict(body["normalized_experience"]),
            rights_basis=str(body["rights_basis"]),
            rights_ref_sha256=str(body["rights_ref_sha256"]),
            privacy_review_sha256=str(body["privacy_review_sha256"]),
            source_review_sha256=str(body["source_review_sha256"]),
            permitted_uses=list(body["permitted_uses"]),
            deidentification_attested=bool(body.get("deidentification_attested", False)),
            raw_payload_included=bool(body.get("raw_payload_included", False)),
            approved_by=str(body["approved_by"]),
        )

    def actionnet_create_global_release(self, body: dict[str, Any]) -> dict[str, Any]:
        return self.learning_network.create_global_training_release(
            str(body["release_id"]),
            list(body["global_record_ids"]),
            str(body["model_target"]),
            protected_evaluation_reservation_sha256=str(
                body["protected_evaluation_reservation_sha256"]
            ),
            dataset_overlap_report_sha256=str(body["dataset_overlap_report_sha256"]),
            release_manager_id=str(body["release_manager_id"]),
        )

    def c1_register_version(self, body: dict[str, Any]) -> dict[str, Any]:
        return self.learning_network.register_c1_version(
            str(body["model_id"]),
            str(body["base_model"]),
            str(body["model_lineage"]),
            str(body["training_release_id"]),
            artifact_sha256=str(body["artifact_sha256"]),
            adapter_sha256=body.get("adapter_sha256"),
            evaluation_sha256=str(body["evaluation_sha256"]),
            license_id=str(body["license_id"]),
            safety_gate=str(body["safety_gate"]),
            performance_gate=str(body["performance_gate"]),
            transfer_gate=str(body["transfer_gate"]),
            protected_evaluation_complete=bool(
                body.get("protected_evaluation_complete", False)
            ),
            created_by=str(body["created_by"]),
            predecessor_model_id=body.get("predecessor_model_id"),
            institution_specific_weight_updates_required=bool(
                body.get("institution_specific_weight_updates_required", False)
            ),
            online_weight_updates_allowed=bool(
                body.get("online_weight_updates_allowed", False)
            ),
        )

    def c1_record_disposition(self, body: dict[str, Any]) -> dict[str, Any]:
        return self.learning_network.record_c1_disposition(
            str(body["model_id"]),
            str(body["disposition"]),
            evidence_ref_sha256=str(body["evidence_ref_sha256"]),
            rationale=str(body["rationale"]),
            actor_id=str(body["actor_id"]),
            rollback_model_id=body.get("rollback_model_id"),
        )

    def actionnet_list_mechanisms(self, body: dict[str, Any]) -> dict[str, Any]:
        return {
            "items": self.actionnet_product.list_mechanisms(str(body["tenant_id"])),
            "binding_authority": False,
        }

    def actionnet_list_institutional_ir(self, body: dict[str, Any]) -> dict[str, Any]:
        return {
            "items": self.actionnet_product.list_institutional_ir(
                str(body["tenant_id"]),
                include_protected=bool(body.get("include_protected", False)),
            ),
            "binding_authority": False,
        }

    def actionnet_list_experiences(self, body: dict[str, Any]) -> dict[str, Any]:
        return {
            "items": self.actionnet_product.list_experiences(
                str(body["tenant_id"]), include_protected=bool(body.get("include_protected", False))
            ),
            "binding_authority": False,
        }

    def actionnet_audit(self, body: dict[str, Any]) -> dict[str, Any]:
        tenant_id = str(body["tenant_id"])
        return {
            "items": self.actionnet_product.audit_events(tenant_id),
            "chain_valid": self.actionnet_product.verify_audit_chain(tenant_id),
            "binding_authority": False,
        }

    def status(self) -> dict[str, Any]:
        candidates = self.registry.list_candidates()
        mechanisms = self.registry.list_mechanisms()
        audit = self.registry.audit_events()
        return {
            "status": "OK",
            "counts": {
                "candidates": len(candidates),
                "approved_mechanisms": len(mechanisms),
                "active_mechanisms": sum(row["active"] for row in mechanisms),
                "audit_events": len(audit),
                "institutional_worlds": self.worlds.count_worlds(),
                "episodic_memories": self.memory.count_entries(),
                "kernel_tokens_consumed": self.kernel_authority.consumed_count(),
                "kernel_tokens_issued": self.kernel_authority.issued_count(),
                "outbox_pending": len(self.outbox.list_messages(status="PENDING")),
                "shadow_cycles": self.shadow_cycles.count_cycles(),
                "federation": self.federation.counts(),
                "agent_gateway": self.agent_gateway.counts(),
                "actionnet_product": self.actionnet_product.counts(),
                "actionnet_learning_network": self.learning_network.counts(),
            },
            "cerebrum": {
                "system_role": "NON_AUTHORITATIVE_INSTITUTIONAL_INTELLIGENCE_SYSTEM",
                "provider": type(self.c1_provider).__name__,
                "model_lineage": self.c1_model_lineage,
                "c1": {
                    "role": "LEARNED_MODEL_LAYER",
                    "provider": type(self.c1_provider).__name__,
                    "model_lineage": self.c1_model_lineage,
                    "historical_component_name": "Cerebrum learned component",
                    "binding_authority": False,
                },
                "state_engine": "REFERENCE_AVAILABLE_NOT_PERSISTENTLY_WIRED",
                "provenance": "REFERENCE_AVAILABLE_NOT_PERSISTENTLY_WIRED",
                "historical_status_fields_preserved": True,
                "mode": "SHADOW",
                "binding_authority": False,
            },
            "audit_chain_valid": self.registry.verify_audit_chain(),
            "binding_authority": False,
        }


class _Handler(BaseHTTPRequestHandler):
    server: "EDONHTTPServer"

    def _json(self, status: int, payload: Any) -> None:
        data = json.dumps(payload, indent=2, sort_keys=True).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def _body(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length", "0"))
        if length <= 0 or length > 5_000_000:
            raise ValueError("request body must be between 1 byte and 5 MB")
        body = json.loads(self.rfile.read(length).decode("utf-8"))
        if not isinstance(body, dict):
            raise ValueError("request body must be a JSON object")
        return body

    def _authorize(self, permission: str) -> bool:
        token = self.headers.get("Authorization", "")
        supplied = token.removeprefix("Bearer ") if token.startswith("Bearer ") else ""
        principal = next(
            (
                configured_principal
                for configured_token, configured_principal in self.server.api_keys.items()
                if supplied and hmac.compare_digest(supplied, configured_token)
            ),
            None,
        )
        if isinstance(principal, dict):
            role = str(principal.get("role", ""))
            tenant_id = principal.get("tenant_id")
        else:
            role = principal
            tenant_id = None
        if role is None:
            self._json(HTTPStatus.UNAUTHORIZED, {"error": "invalid API token"})
            return False
        self.authenticated_role = role
        self.authenticated_tenant = str(tenant_id) if tenant_id else None
        self.authenticated_actor = "api-key-" + hashlib.sha256(supplied.encode("utf-8")).hexdigest()[:16]
        if not authorized(role, permission):
            self._json(HTTPStatus.FORBIDDEN, {"error": "role is not authorized", "role": role})
            return False
        return True

    def do_GET(self) -> None:
        path = urlparse(self.path).path
        if path == "/health":
            self._json(HTTPStatus.OK, {"status": "healthy", "binding_authority": False})
            return
        if path == "/":
            data = DASHBOARD_HTML.encode("utf-8")
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'unsafe-inline'; style-src 'unsafe-inline'")
            self.end_headers()
            self.wfile.write(data)
            return
        if not self._authorize("read"):
            return
        routes = {
            "/api/whoami": lambda: {
                "role": self.authenticated_role,
                "actor_id": self.authenticated_actor,
                "tenant_id": self.authenticated_tenant,
                "binding_authority": False,
            },
            "/api/status": lambda: self.server.service.status(),
            "/api/candidates": lambda: {"items": self.server.service.registry.list_candidates()},
            "/api/mechanisms": lambda: {"items": self.server.service.registry.list_mechanisms()},
            "/api/audit": lambda: {"items": self.server.service.registry.audit_events()},
            "/api/gateway/capabilities": lambda: self.server.service.agent_gateway.capabilities(),
            "/api/gateway/vendors": lambda: self.server.service.agent_gateway.vendors(),
        }
        if path not in routes:
            self._json(HTTPStatus.NOT_FOUND, {"error": "route not found"})
            return
        self._json(HTTPStatus.OK, routes[path]())

    def do_POST(self) -> None:
        path = urlparse(self.path).path
        routes = {
            "/api/compile": ("compile", self.server.service.compile),
            "/api/reviews": ("review", self.server.service.review),
            "/api/promotions": ("promote", self.server.service.promote),
            "/api/rollbacks": ("rollback", self.server.service.rollback),
            "/api/simulations": ("simulate", self.server.service.simulate),
            "/api/actionnet": ("generate", self.server.service.actionnet),
            "/api/shadow": ("shadow", self.server.service.shadow),
            "/api/gaps": ("gaps", self.server.service.gaps),
            "/api/worlds": ("world", self.server.service.create_world),
            "/api/world-events": ("world", self.server.service.append_world_event),
            "/api/world-restores": ("world", self.server.service.restore_world),
            "/api/world-state": ("world", self.server.service.world_state),
            "/api/world-history": ("world", self.server.service.world_history),
            "/api/world-verify": ("world", self.server.service.verify_world),
            "/api/memories": ("memory", self.server.service.record_memory),
            "/api/memory-query": ("memory", self.server.service.query_memory),
            "/api/memory-tombstones": ("memory", self.server.service.tombstone_memory),
            "/api/operations/bootstrap": ("operations", self.server.service.bootstrap_operations),
            "/api/operations/initialize": ("operations", self.server.service.initialize_operations),
            "/api/operations/state": ("operations", self.server.service.operational_state),
            "/api/observations": ("operations", self.server.service.ingest_observation),
            "/api/agents": ("operations", self.server.service.register_agent),
            "/api/agent-status": ("operations", self.server.service.set_agent_status),
            "/api/resources": ("operations", self.server.service.register_resource),
            "/api/goals": ("operations", self.server.service.create_goal),
            "/api/goal-transitions": ("operations", self.server.service.transition_goal),
            "/api/plans": ("operations", self.server.service.create_plan),
            "/api/replans": ("operations", self.server.service.replan),
            "/api/ready-steps": ("operations", self.server.service.ready_steps),
            "/api/resource-allocations": ("operations", self.server.service.allocate_resources),
            "/api/step-assignments": ("operations", self.server.service.assign_step),
            "/api/assignment-proposals": ("operations", self.server.service.assignment_proposals),
            "/api/dispatches": ("operations", self.server.service.dispatch_step),
            "/api/step-starts": ("operations", self.server.service.start_step),
            "/api/step-outcomes": ("operations", self.server.service.record_outcome),
            "/api/step-cancellations": ("operations", self.server.service.cancel_step),
            "/api/operations/monitor": ("operations", self.server.service.monitor_operations),
            "/api/operations/monitor-record": ("operations", self.server.service.record_monitoring_cycle),
            "/api/kernel/tokens": ("authorize", self.server.service.issue_kernel_token),
            "/api/kernel/worlds": ("kernel_commit", self.server.service.kernel_create_world),
            "/api/kernel/world-events": ("kernel_commit", self.server.service.kernel_append_world_event),
            "/api/supervisor/cycles": ("shadow", self.server.service.run_shadow_supervisor),
            "/api/federation/scopes": ("federation", self.server.service.register_federation_scope),
            "/api/federation/projections": ("federation", self.server.service.project_federation_scope),
            "/api/federation/aggregates": ("federation", self.server.service.aggregate_federation_scope),
            "/api/federation/routes": ("federation", self.server.service.route_federation_decision),
            "/api/federation/escalation-events": (
                "federation", self.server.service.record_federation_escalation_event
            ),
            "/api/federation/escalations": (
                "federation", self.server.service.list_federation_escalations
            ),
            "/api/optimization/candidates": ("optimize", self.server.service.optimization_candidate),
            "/api/gateway/connectors": (
                "gateway_admin", self.server.service.gateway_register_connector
            ),
            "/api/gateway/connectors/status": (
                "gateway_admin", self.server.service.gateway_set_connector_status
            ),
            "/api/gateway/messages": (
                "gateway_ingest", self.server.service.gateway_ingest
            ),
            "/api/gateway/egress": (
                "gateway_egress", self.server.service.gateway_stage_egress
            ),
            "/api/gateway/connectors/query": (
                "gateway_read", self.server.service.gateway_list_connectors
            ),
            "/api/gateway/messages/query": (
                "gateway_read", self.server.service.gateway_list_messages
            ),
            "/api/gateway/audit": (
                "gateway_admin", self.server.service.gateway_audit
            ),
            "/api/actionnet-platform/mechanisms": (
                "actionnet_author", self.server.service.actionnet_register_mechanism
            ),
            "/api/actionnet-platform/institutional-ir": (
                "actionnet_author", self.server.service.actionnet_register_institutional_ir
            ),
            "/api/actionnet-platform/compositions": (
                "actionnet_author", self.server.service.actionnet_register_composition
            ),
            "/api/actionnet-platform/worlds/generate": (
                "actionnet_author", self.server.service.actionnet_generate_world
            ),
            "/api/actionnet-platform/compositions/execute": (
                "actionnet_author", self.server.service.actionnet_execute_composition
            ),
            "/api/actionnet-platform/counterfactuals/generate": (
                "actionnet_author", self.server.service.actionnet_generate_counterfactuals
            ),
            "/api/actionnet-platform/behavior/scenarios": (
                "actionnet_author", self.server.service.actionnet_generate_behavior_scenario
            ),
            "/api/actionnet-platform/intake": (
                "actionnet_intake", self.server.service.actionnet_ingest_governed_abstraction
            ),
            "/api/actionnet-platform/experiences": (
                "actionnet_author", self.server.service.actionnet_record_experience
            ),
            "/api/actionnet-platform/reviews": (
                "actionnet_review", self.server.service.actionnet_review_experience
            ),
            "/api/actionnet-platform/overlap-checks": (
                "actionnet_custody", self.server.service.actionnet_overlap_check
            ),
            "/api/actionnet-platform/training-eligibility": (
                "actionnet_release", self.server.service.actionnet_training_eligibility
            ),
            "/api/actionnet-platform/quarantine": (
                "actionnet_custody", self.server.service.actionnet_quarantine_experience
            ),
            "/api/actionnet-platform/exposures": (
                "actionnet_custody", self.server.service.actionnet_record_exposure
            ),
            "/api/actionnet-platform/coverage": (
                "actionnet_read", self.server.service.actionnet_coverage
            ),
            "/api/actionnet-platform/coverage/freeze": (
                "actionnet_curriculum", self.server.service.actionnet_freeze_coverage
            ),
            "/api/actionnet-platform/acquisition": (
                "actionnet_curriculum", self.server.service.actionnet_recommend_acquisition
            ),
            "/api/actionnet-platform/interventions": (
                "actionnet_intervention", self.server.service.actionnet_record_intervention
            ),
            "/api/actionnet-platform/releases": (
                "actionnet_release", self.server.service.actionnet_create_release
            ),
            "/api/actionnet-network/promotions": (
                "actionnet_global", self.server.service.actionnet_promote_global
            ),
            "/api/actionnet-network/releases": (
                "actionnet_global", self.server.service.actionnet_create_global_release
            ),
            "/api/c1/versions": (
                "c1_release", self.server.service.c1_register_version
            ),
            "/api/c1/dispositions": (
                "c1_release", self.server.service.c1_record_disposition
            ),
            "/api/actionnet-platform/mechanisms/query": (
                "actionnet_read", self.server.service.actionnet_list_mechanisms
            ),
            "/api/actionnet-platform/institutional-ir/query": (
                "actionnet_read", self.server.service.actionnet_list_institutional_ir
            ),
            "/api/actionnet-platform/experiences/query": (
                "actionnet_read", self.server.service.actionnet_list_experiences
            ),
            "/api/actionnet-platform/audit": (
                "actionnet_custody", self.server.service.actionnet_audit
            ),
        }
        route = routes.get(path)
        if not route:
            self._json(HTTPStatus.NOT_FOUND, {"error": "route not found"})
            return
        permission, operation = route
        if not self._authorize(permission):
            return
        try:
            body = self._body()
            if self.authenticated_tenant:
                requested_tenant = body.get("tenant_id")
                if requested_tenant is not None and str(requested_tenant) != self.authenticated_tenant:
                    raise ValueError("authenticated principal is bound to a different tenant")
                if path.startswith("/api/actionnet-platform/"):
                    body["tenant_id"] = self.authenticated_tenant
                if path == "/api/actionnet-network/promotions":
                    body["tenant_id"] = self.authenticated_tenant
                if path.startswith("/api/gateway/"):
                    body["tenant_id"] = self.authenticated_tenant
            if path.startswith("/api/actionnet-platform/"):
                body["actor_role"] = self.authenticated_role
            if path == "/api/reviews":
                body["reviewer_id"] = self.authenticated_actor
                body["reviewer_role"] = self.authenticated_role
            elif path == "/api/promotions":
                body["promoter_id"] = self.authenticated_actor
            elif path == "/api/rollbacks":
                body["actor_id"] = self.authenticated_actor
            elif path in {
                "/api/worlds", "/api/world-events", "/api/world-restores",
                "/api/memories", "/api/memory-query", "/api/memory-tombstones",
                "/api/operations/bootstrap", "/api/operations/initialize", "/api/observations",
                "/api/agents", "/api/agent-status", "/api/resources", "/api/goals",
                "/api/goal-transitions", "/api/plans", "/api/replans",
                "/api/resource-allocations", "/api/step-assignments", "/api/step-starts",
                "/api/dispatches", "/api/step-outcomes", "/api/step-cancellations",
                "/api/operations/monitor-record",
                "/api/kernel/worlds", "/api/kernel/world-events",
                "/api/federation/escalation-events",
                "/api/gateway/connectors",
                "/api/gateway/connectors/status",
                "/api/gateway/messages",
                "/api/gateway/egress",
                "/api/actionnet-platform/mechanisms",
                "/api/actionnet-platform/institutional-ir",
                "/api/actionnet-platform/compositions",
                "/api/actionnet-platform/worlds/generate",
                "/api/actionnet-platform/compositions/execute",
                "/api/actionnet-platform/counterfactuals/generate",
                "/api/actionnet-platform/behavior/scenarios",
                "/api/actionnet-platform/intake",
                "/api/actionnet-platform/experiences",
                "/api/actionnet-platform/overlap-checks",
                "/api/actionnet-platform/quarantine",
                "/api/actionnet-platform/exposures",
                "/api/actionnet-platform/coverage/freeze",
                "/api/actionnet-platform/acquisition",
                "/api/actionnet-platform/interventions",
                "/api/c1/versions",
            }:
                body["actor_id"] = self.authenticated_actor
                body["created_by"] = self.authenticated_actor
            if path == "/api/actionnet-platform/reviews":
                body["reviewer_id"] = self.authenticated_actor
                body["reviewer_role"] = self.authenticated_role
            if path in {
                "/api/actionnet-platform/training-eligibility",
                "/api/actionnet-platform/releases",
                "/api/actionnet-network/releases",
            }:
                body["release_manager_id"] = self.authenticated_actor
            if path == "/api/actionnet-network/promotions":
                body["approved_by"] = self.authenticated_actor
            if path == "/api/c1/dispositions":
                body["actor_id"] = self.authenticated_actor
            if path == "/api/kernel/tokens":
                body["issuer_id"] = self.authenticated_actor
            if path in {"/api/memories", "/api/observations", "/api/step-outcomes"}:
                permitted = ROLE_MEMORY_SENSITIVITIES.get(self.authenticated_role, set())
                requested_sensitivity = str(body.get("sensitivity", "INTERNAL")).upper()
                if requested_sensitivity not in permitted:
                    raise ValueError("role is not authorized for requested memory sensitivity")
            elif path == "/api/memory-query":
                permitted = ROLE_MEMORY_SENSITIVITIES.get(self.authenticated_role, set())
                requested = {str(item).upper() for item in body.get("allowed_sensitivities", [])}
                if requested and not requested.issubset(permitted):
                    raise ValueError("role is not authorized for requested memory sensitivities")
                body["allowed_sensitivities"] = sorted(requested or permitted)
            if path in {
                "/api/actionnet-platform/experiences/query",
                "/api/actionnet-platform/institutional-ir/query",
            }:
                include_protected = bool(body.get("include_protected", False))
                if include_protected and self.authenticated_role not in {
                    "ACTIONNET_CUSTODIAN", "ADMIN"
                }:
                    raise ValueError("role is not authorized to list protected experiences")
            if path in {
                "/api/actionnet-platform/worlds/generate",
                "/api/actionnet-platform/institutional-ir",
                "/api/actionnet-platform/experiences",
            } and bool(body.get("protected", False)):
                if self.authenticated_role not in {"ACTIONNET_CUSTODIAN", "ADMIN"}:
                    raise ValueError("only the ActionNet custodian may create protected records")
            result = operation(body)
        except (KeyError, TypeError, ValueError, RuntimeError, json.JSONDecodeError) as exc:
            self._json(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return
        self._json(HTTPStatus.OK, result)

    def log_message(self, format: str, *args: Any) -> None:
        return


class EDONHTTPServer(ThreadingHTTPServer):
    def __init__(
        self,
        address: tuple[str, int],
        service: PlatformService,
        api_keys: dict[str, str | dict[str, str]],
    ):
        if not api_keys:
            raise ValueError("at least one API key is required")
        if any(len(token) < 16 for token in api_keys):
            raise ValueError("every API key must contain at least 16 characters")
        configured_roles = [
            str(principal.get("role", "")) if isinstance(principal, dict) else principal
            for principal in api_keys.values()
        ]
        if any(role not in ROLE_PERMISSIONS for role in configured_roles):
            raise ValueError("API key mapping contains an unknown role")
        for principal in api_keys.values():
            if isinstance(principal, dict):
                extra = set(principal) - {"role", "tenant_id"}
                if extra or not principal.get("role"):
                    raise ValueError("API principal object may contain role and tenant_id only")
                if principal.get("tenant_id") is not None and not str(principal["tenant_id"]).strip():
                    raise ValueError("API principal tenant_id cannot be empty")
        self.service = service
        self.api_keys = dict(api_keys)
        super().__init__(address, _Handler)


def run_server(
    state_dir: Path | str,
    host: str,
    port: int,
    api_keys: dict[str, str | dict[str, str]],
) -> None:
    server = EDONHTTPServer((host, port), PlatformService(state_dir), api_keys)
    try:
        server.serve_forever()
    finally:
        server.server_close()