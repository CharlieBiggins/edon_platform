import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from edon.cerebrum import Certificate
from edon.compiler import CompilerCandidate, TruthLayer
from edon.ir import Decision, InstitutionalMechanism, SemanticState
from edon.runtime import RuntimeProposal
from edon.safety import GateResult


class ContractTests(unittest.TestCase):
    def test_certificate_cannot_be_binding(self):
        with self.assertRaises(ValueError):
            Certificate(SemanticState.TRUE, Decision.ALLOW, binding_authority=True)

    def test_runtime_proposal_cannot_be_binding(self):
        with self.assertRaises(ValueError):
            RuntimeProposal("p", "v1", {}, "sha256:" + "0" * 64, "sha256:" + "1" * 64, True)

    def test_high_risk_compiler_candidate_requires_review(self):
        mechanism = InstitutionalMechanism("m", "v1", risk_class="HIGH")
        candidate = CompilerCandidate("c", mechanism, (), (TruthLayer.NORMATIVE,), 0.99)
        self.assertTrue(candidate.human_review_required)

    def test_gate_requires_all_checks(self):
        self.assertTrue(GateResult("g", {"a": True, "b": True}).passed)
        self.assertFalse(GateResult("g", {"a": True, "b": False}).passed)


if __name__ == "__main__":
    unittest.main()