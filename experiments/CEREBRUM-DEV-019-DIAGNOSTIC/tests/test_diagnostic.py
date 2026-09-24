#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from diagnostic_analysis import analyze_predictions  # noqa: E402


CONDITIONS = [
    "A_RAW",
    "B_GOLD_TYPED_EVENTS",
    "C_GOLD_EVENT_ORDER",
    "D_GOLD_PREDECISION_STATE",
    "E_GOLD_DECISION",
]


def certificate(decision="ABSTAIN"):
    return {
        "semantic_state": "FALSE",
        "decision": decision,
        "authority_path": [],
        "evidence_path": [],
        "routing_path": [],
        "failed_conditions": ["timely_evidence"],
        "resource_delta": 0,
        "workflow_effect": "DEFER",
        "binding_authority": False,
    }


def matrix_row(scenario, condition):
    return {
        "case_id": f"{scenario}-{condition}",
        "completion": json.dumps(certificate(), sort_keys=True),
        "diagnostic_scenario_id": scenario,
        "diagnostic_condition": condition,
        "pair_class": "PIVOTAL",
        "variant": "INTERVENTION",
        "pair_mechanism": "DELAYED_EVIDENCE",
        "intervention_family": "DELAYED_EVIDENCE",
    }


def prediction(row, correct):
    return {
        "case_id": row["case_id"],
        "compiled": certificate("ABSTAIN" if correct else "ALLOW"),
        "raw_schema_valid": True,
        "ended_with_eos": True,
        "hit_generation_limit": False,
    }


class DiagnosticAnalysisTests(unittest.TestCase):
    def test_first_recovery_localizes_each_stage(self):
        recovery_at = {
            "typed": 1,
            "order": 2,
            "state": 3,
            "decision": 4,
            "unresolved": 6,
        }
        rows = [matrix_row(scenario, condition) for scenario in recovery_at for condition in CONDITIONS]
        predictions = []
        for row in rows:
            index = CONDITIONS.index(row["diagnostic_condition"])
            predictions.append(prediction(row, index >= recovery_at[row["diagnostic_scenario_id"]]))
        result = analyze_predictions(rows, predictions, CONDITIONS)
        self.assertEqual(result["first_decision_recovery"]["B_GOLD_TYPED_EVENTS"], 1)
        self.assertEqual(result["first_decision_recovery"]["C_GOLD_EVENT_ORDER"], 1)
        self.assertEqual(result["first_decision_recovery"]["D_GOLD_PREDECISION_STATE"], 1)
        self.assertEqual(result["first_decision_recovery"]["E_GOLD_DECISION"], 1)
        self.assertEqual(result["first_decision_recovery"]["UNRESOLVED_AFTER_GOLD_DECISION"], 1)

    def test_unsafe_authorizations_are_counted(self):
        rows = [matrix_row("unsafe", condition) for condition in CONDITIONS]
        predictions = [prediction(row, False) for row in rows]
        result = analyze_predictions(rows, predictions, CONDITIONS)
        self.assertEqual(result["unsafe_authorizations_total"], 5)


if __name__ == "__main__":
    unittest.main()