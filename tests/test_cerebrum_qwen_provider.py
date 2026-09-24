import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from edon.api.server import PlatformService
from edon.cerebrum import (
    OperationsProposalAdapter,
    OperationsProposalError,
    QwenOperationsProvider,
    configured_operations_provider,
)


class FixtureBackend:
    def __init__(self, response: str):
        self.response = response
        self.messages = None

    def generate(self, messages):
        self.messages = messages
        return self.response


class QwenProviderTests(unittest.TestCase):
    def test_valid_model_json_enters_non_binding_adapter(self):
        backend = FixtureBackend(json.dumps({
            "proposal_type": "DISPATCH_STEP",
            "payload": {"plan_id": "plan-a", "step_id": "step-a", "agent_id": "agent-a"},
            "rationale": "The registered agent is feasible for the ready operational step.",
            "confidence": 0.81,
            "binding_authority": False,
        }))
        provider = QwenOperationsProvider(backend)
        adapter = OperationsProposalAdapter(provider, model_lineage="build-001:test-adapter")
        proposal = adapter.propose({
            "mode": "SHADOW",
            "assignment_proposals": [{
                "plan_id": "plan-a",
                "step_id": "step-a",
                "recommended_agent_id": "agent-a",
                "dispatchable": True,
            }],
        })
        self.assertEqual(proposal["proposal_type"], "DISPATCH_STEP")
        self.assertFalse(proposal["binding_authority"])
        self.assertEqual(proposal["model_lineage"], "build-001:test-adapter")
        self.assertIn("no authority to execute", backend.messages[0]["content"])

    def test_invalid_generation_fails_closed_to_abstain(self):
        provider = QwenOperationsProvider(FixtureBackend("not json"))
        adapter = OperationsProposalAdapter(provider, model_lineage="build-001:invalid")
        proposal = adapter.propose({"mode": "SHADOW"})
        self.assertEqual(proposal["proposal_type"], "ABSTAIN")
        self.assertEqual(proposal["confidence"], 0.0)
        self.assertFalse(proposal["binding_authority"])
        self.assertIsNotNone(provider.last_error)

    def test_authority_smuggling_still_rejected_by_adapter(self):
        backend = FixtureBackend(json.dumps({
            "proposal_type": "ABSTAIN",
            "payload": {},
            "rationale": "This malformed proposal attempts to carry forbidden authority.",
            "confidence": 0.5,
            "binding_authority": False,
            "execution_token": "forged",
        }))
        adapter = OperationsProposalAdapter(
            QwenOperationsProvider(backend), model_lineage="build-001:unsafe"
        )
        with self.assertRaisesRegex(OperationsProposalError, "authority fields"):
            adapter.propose({"mode": "SHADOW"})

    def test_nested_authority_smuggling_is_rejected(self):
        backend = FixtureBackend(json.dumps({
            "proposal_type": "CREATE_PLAN",
            "payload": {
                "plan_id": "plan-a",
                "goal_id": "goal-a",
                "horizon_start": "2026-08-25T00:00:00+00:00",
                "steps": [{
                    "step_id": "step-a",
                    "action": "Analyze the registered institutional state.",
                    "execution_token": "forged-nested-token",
                }],
            },
            "rationale": "The plan decomposes the requested analysis into one bounded step.",
            "confidence": 0.7,
            "binding_authority": False,
        }))
        adapter = OperationsProposalAdapter(
            QwenOperationsProvider(backend), model_lineage="build-001:nested-unsafe"
        )
        with self.assertRaisesRegex(OperationsProposalError, r"payload.steps\[0\].execution_token"):
            adapter.propose({"mode": "SHADOW"})

    def test_ungrounded_dispatch_fails_closed(self):
        backend = FixtureBackend(json.dumps({
            "proposal_type": "DISPATCH_STEP",
            "payload": {"plan_id": "invented", "step_id": "invented", "agent_id": "invented"},
            "rationale": "This dispatch invents identifiers that were not present in context.",
            "confidence": 0.9,
            "binding_authority": False,
        }))
        provider = QwenOperationsProvider(backend)
        proposal = OperationsProposalAdapter(
            provider, model_lineage="build-001:ungrounded"
        ).propose({"mode": "SHADOW", "assignment_proposals": []})
        self.assertEqual(proposal["proposal_type"], "ABSTAIN")
        self.assertIn("not grounded", provider.last_error)

    def test_learned_environment_requires_explicit_lineage(self):
        with self.assertRaisesRegex(OperationsProposalError, "MODEL_LINEAGE"):
            configured_operations_provider({"EDON_CEREBRUM_PROVIDER": "qwen"})

    def test_learned_environment_configuration_is_lazy(self):
        provider, lineage = configured_operations_provider({
            "EDON_CEREBRUM_PROVIDER": "qwen",
            "EDON_CEREBRUM_MODEL_LINEAGE": "cerebrum-build-001:untrained-smoke",
            "EDON_CEREBRUM_LOAD_IN_4BIT": "1",
        })
        self.assertEqual(type(provider).__name__, "QwenOperationsProvider")
        self.assertEqual(lineage, "cerebrum-build-001:untrained-smoke")
        self.assertIsNone(provider.backend._model)

    def test_platform_accepts_injected_provider_and_reports_shadow_mode(self):
        provider = QwenOperationsProvider(FixtureBackend(json.dumps({
            "proposal_type": "ABSTAIN",
            "payload": {},
            "rationale": "The fixture intentionally abstains during the integration check.",
            "confidence": 1.0,
            "binding_authority": False,
        })))
        with tempfile.TemporaryDirectory() as directory:
            service = PlatformService(
                directory,
                operations_provider=provider,
                model_lineage="cerebrum-build-001:fixture",
            )
            status = service.status()["cerebrum"]
            self.assertEqual(status["provider"], "QwenOperationsProvider")
            self.assertEqual(status["mode"], "SHADOW")
            self.assertFalse(status["binding_authority"])


if __name__ == "__main__":
    unittest.main()