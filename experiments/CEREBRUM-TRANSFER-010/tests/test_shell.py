from __future__ import annotations

import unittest

from preflight import build_report
from transfer010 import PASS_STATUS, ROOT, forbidden_materialized_paths, read_json, verify_dev010_summary


class Transfer010ShellTests(unittest.TestCase):
    def test_shell_readiness_passes(self):
        report = build_report()
        self.assertEqual(report["controls_passed"], report["control_count"])
        self.assertEqual(
            report["status"],
            "SHELL_READY_MATERIALIZATION_UNAUTHORIZED_PENDING_DEV010_PASS_AND_INDEPENDENT_COMMITMENTS",
        )

    def test_no_protected_material_is_present(self):
        self.assertEqual(forbidden_materialized_paths(), [])
        reservation = read_json(ROOT / "reservation.json")
        self.assertFalse(reservation["cases_materialized"])
        self.assertFalse(reservation["labels_materialized"])
        self.assertFalse(reservation["materialization_authorized"])

    def test_candidate_slots_are_blank(self):
        registry = read_json(ROOT / "candidate_registry.json")
        self.assertEqual(registry["status"], "PENDING_DEV010_TWO_SEED_PASS")
        self.assertTrue(all(row["adapter_sha256"] is None for row in registry["candidates"]))
        self.assertTrue(all(row["frozen"] is False for row in registry["candidates"]))

    def test_two_frontier_baselines_are_required_but_blank(self):
        contract = read_json(ROOT / "config" / "baseline-contract.json")
        registry = read_json(ROOT / "baseline_registry.json")
        self.assertEqual(contract["frontier_requirements"]["condition_count"], 2)
        self.assertTrue(contract["frontier_requirements"]["distinct_providers"])
        frontier = registry["conditions"][3:]
        self.assertEqual([row["condition"] for row in frontier], ["frontier_general_primary", "frontier_general_secondary"])
        self.assertTrue(all(row["provider"] is None and row["model"] is None for row in frontier))

    def test_narrow_scope_is_explicit(self):
        gates = read_json(ROOT / "config" / "transfer-gates.json")
        self.assertTrue(all(gates["scope_exclusions"].values()))
        self.assertEqual(gates["case_count"], 192)
        self.assertEqual(gates["governance_form_count"], 4)

    def test_target_specific_repair_is_prohibited(self):
        prohibited = read_json(ROOT / "lineage" / "prohibited-predecessors.json")
        for action in ("gradient_update", "prompt_repair", "parser_patch", "output_repair", "threshold_tuning", "case_specific_analysis"):
            self.assertIn(action, prohibited["prohibited_post_materialization_actions"])

    def test_failed_dev010_summary_is_rejected(self):
        summary = {
            "protocol_id": "CEREBRUM-DEV-010",
            "status": "DEV010_REPAIR_NOT_ESTABLISHED",
            "passed": False,
            "registered_seeds": [26090401, 26090402],
            "seed_results": [],
        }
        with self.assertRaises(ValueError):
            verify_dev010_summary(summary)

    def test_valid_dev010_summary_shape_is_accepted(self):
        summary = {
            "protocol_id": "CEREBRUM-DEV-010",
            "status": PASS_STATUS,
            "passed": True,
            "registered_seeds": [26090401, 26090402],
            "seed_results": [
                {"seed": 26090401, "gate": {"passed": True}, "unsafe_authorizations": 0},
                {"seed": 26090402, "gate": {"passed": True}, "unsafe_authorizations": 0},
            ],
        }
        verify_dev010_summary(summary)

    def test_protected_input_schema_excludes_answer_fields(self):
        schema = read_json(ROOT / "schemas" / "protected-input.schema.json")
        self.assertFalse(schema["additionalProperties"])
        self.assertNotIn("expected", schema["properties"])
        self.assertNotIn("label", schema["properties"])
        self.assertNotIn("oracle", schema["properties"])


if __name__ == "__main__":
    unittest.main()