from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from interface_analysis import CERTIFICATE_FIELDS, analyze  # noqa: E402


def certificate(decision="ABSTAIN"):
    return {
        "semantic_state": "FALSE",
        "decision": decision,
        "authority_path": ["requester", "delegator", "institution"],
        "evidence_path": ["source", "FALSE"],
        "routing_path": ["source", "target"],
        "failed_conditions": ["POLICY"],
        "resource_delta": 0,
        "workflow_effect": "BLOCKED",
        "binding_authority": False,
    }


def row(scenario, condition, arm="REPRESENTATION"):
    return {
        "case_id": f"{scenario}-{condition}",
        "completion": json.dumps(certificate(), sort_keys=True),
        "calibration_scenario_id": scenario,
        "calibration_condition": condition,
        "calibration_arm": arm,
        "pair_mechanism": "POLICY_CHANGE",
    }


def prediction(expected, decision="ABSTAIN", exact=True):
    value = certificate(decision)
    if not exact:
        value["workflow_effect"] = "ADVANCE"
    return {
        "case_id": expected["case_id"],
        "compiled": value,
        "raw_schema_valid": True,
        "ended_with_eos": True,
        "hit_generation_limit": False,
        "prompt_token_count": 100,
        "generated_token_count": 50,
    }


class InterfaceAnalysisTests(unittest.TestCase):
    def setUp(self):
        self.conditions = ["RAW_DOCKET", "TYPED_JSON", "AUTHENTICATED_DECISION_FIDELITY"]
        self.rows = [
            row(str(index), condition, "DECISION_FIDELITY" if condition.startswith("AUTHENTICATED") else "REPRESENTATION")
            for index in range(20)
            for condition in self.conditions
        ]
        self.gates = {
            "decision_noninferiority_margin": 0.05,
            "semantic_noninferiority_margin": 0.05,
            "raw_correct_preservation_floor": 0.95,
            "decision_agreement_floor": 0.90,
            "raw_schema_validity_floor": 1.0,
            "unsafe_authorization_delta_ceiling": 0,
        }
        self.fidelity = {
            "decision_preservation_floor": 0.98,
            "exact_certificate_floor": 0.95,
            "raw_schema_validity_floor": 1.0,
            "unsafe_decision_change_ceiling": 0,
        }

    def test_selects_stable_candidate_and_passes_fidelity(self):
        predictions = [prediction(expected) for expected in self.rows]
        result = analyze(
            self.rows, predictions, "RAW_DOCKET", ["TYPED_JSON"],
            "AUTHENTICATED_DECISION_FIDELITY", self.gates, self.fidelity,
        )
        self.assertEqual(result["selected_representation"], "TYPED_JSON")
        self.assertTrue(result["fidelity_passed"])
        self.assertEqual(set(result["condition_results"]["TYPED_JSON"]["field_accuracy"]), set(CERTIFICATE_FIELDS))

    def test_rejects_candidate_that_breaks_raw_correct_cases(self):
        predictions = []
        for expected in self.rows:
            if expected["calibration_condition"] == "TYPED_JSON" and int(expected["calibration_scenario_id"]) < 3:
                predictions.append(prediction(expected, decision="ALLOW"))
            else:
                predictions.append(prediction(expected))
        result = analyze(
            self.rows, predictions, "RAW_DOCKET", ["TYPED_JSON"],
            "AUTHENTICATED_DECISION_FIDELITY", self.gates, self.fidelity,
        )
        self.assertIsNone(result["selected_representation"])
        self.assertFalse(result["representation_comparisons"]["TYPED_JSON"]["qualified"])


if __name__ == "__main__":
    unittest.main()
