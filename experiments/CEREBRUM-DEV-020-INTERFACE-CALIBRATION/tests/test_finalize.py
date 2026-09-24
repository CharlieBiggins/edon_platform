from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from finalize_result import build_error_audit  # noqa: E402


def certificate(decision="ABSTAIN"):
    return {
        "semantic_state": "UNKNOWN",
        "decision": decision,
        "authority_path": ["requester", "delegator", "institution"],
        "evidence_path": ["source", "UNKNOWN"],
        "routing_path": ["source", "target"],
        "failed_conditions": ["EVIDENCE_UNAVAILABLE"],
        "resource_delta": 0,
        "workflow_effect": "BLOCKED",
        "binding_authority": False,
    }


def expected(scenario, condition):
    return {
        "case_id": f"{scenario}-{condition}",
        "completion": json.dumps(certificate(), sort_keys=True),
        "calibration_scenario_id": scenario,
        "calibration_condition": condition,
        "calibration_arm": "DECISION_FIDELITY" if condition.startswith("AUTHENTICATED") else "REPRESENTATION",
        "pair_mechanism": "DELAYED_EVIDENCE",
    }


def prediction(row, value=None):
    return {
        "case_id": row["case_id"],
        "compiled": value or certificate(),
        "raw_schema_valid": True,
        "ended_with_eos": True,
        "hit_generation_limit": False,
        "prompt_token_count": 100,
        "generated_token_count": 50,
    }


class FinalizeAuditTests(unittest.TestCase):
    def test_counts_selected_failure_and_combined_fidelity(self):
        fidelity = "AUTHENTICATED_DECISION_FIDELITY"
        calibration_rows = [expected("cal", fidelity)]
        calibration_predictions = [prediction(calibration_rows[0])]
        validation_rows = [
            expected("held", "RAW_DOCKET"),
            expected("held", "FAMILIAR_AUGMENTED"),
            expected("held", fidelity),
        ]
        unsafe = certificate("ALLOW")
        validation_predictions = [
            prediction(validation_rows[0], unsafe),
            prediction(validation_rows[1], unsafe),
            prediction(validation_rows[2]),
        ]
        audit = build_error_audit(
            calibration_rows,
            calibration_predictions,
            validation_rows,
            validation_predictions,
            "FAMILIAR_AUGMENTED",
            "RAW_DOCKET",
            fidelity,
        )
        self.assertEqual(audit["heldout"]["failure_count"], 1)
        self.assertEqual(audit["heldout"]["unsafe_failure_count"], 1)
        self.assertEqual(audit["authenticated_decision_fidelity"]["decision_preserved"], 2)


if __name__ == "__main__":
    unittest.main()