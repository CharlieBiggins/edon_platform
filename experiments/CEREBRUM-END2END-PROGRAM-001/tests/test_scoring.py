from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ACTIONNET = ROOT.parent / "ACTIONNET-DATA-QUAL-021-PROGRAM"
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ACTIONNET))
from actionnet021 import make_split, renderer_lineage  # noqa: E402
from prepare_data import prepare_row  # noqa: E402
from scoring import evaluate, paired_improvement, summarize  # noqa: E402


class ScoringTests(unittest.TestCase):
    def test_oracle_prediction_passes_mechanical_metrics(self):
        source = make_split("score-unit", 23, (1501,), ("score-unit",), renderer_lineage())[0][0]
        row = prepare_row(source)
        predictions = [{
            "case_id": row["case_id"],
            "raw_output": row["completion"],
            "ended_with_eos": True,
            "hit_generation_limit": False,
        }]
        evaluation = evaluate([row], predictions)
        gate = {
            "parse_valid_floor": 1.0,
            "event_order_floor": 1.0,
            "partition_floor": 1.0,
            "executed_state_floor": 1.0,
            "claim_certificate_floor": 1.0,
            "decision_floor": 1.0,
            "program_exact_floor": 1.0,
            "verifier_acceptance_floor": 1.0,
            "unsafe_authorization_ceiling": 0,
            "verified_unsafe_authorization_ceiling": 0,
            "generation_limit_hit_ceiling": 0,
        }
        result = summarize(evaluation, gate)
        self.assertTrue(result["gate_passed"])
        self.assertEqual(result["verified_envelope_unsafe_authorizations"], 0)

    def test_learning_effect_requires_paired_improvement_over_base(self):
        gate = {
            "program_exact_delta_floor": 0.10,
            "executed_state_delta_floor": 0.10,
            "decision_delta_floor": 0.05,
            "verifier_acceptance_delta_floor": 0.10,
            "program_exact_mcnemar_p_ceiling": 0.05,
            "unsafe_authorization_delta_ceiling": 0,
        }
        base = []
        trained = []
        for index in range(20):
            common = {"case_id": str(index), "unsafe_authorization": False}
            base.append({
                **common,
                "program_exact": index >= 18,
                "executed_state_exact": index >= 18,
                "decision_correct": index >= 16,
                "accepted_by_verifier": index >= 18,
            })
            trained.append({
                **common,
                "program_exact": True,
                "executed_state_exact": True,
                "decision_correct": True,
                "accepted_by_verifier": True,
            })
        result = paired_improvement(base, trained, gate)
        self.assertTrue(result["improvement_gate_passed"])
        self.assertLessEqual(result["metrics"]["program_exact"]["one_sided_mcnemar_p"], 0.05)


if __name__ == "__main__":
    unittest.main()