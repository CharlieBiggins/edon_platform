#!/usr/bin/env python3
from __future__ import annotations

import unittest

from preflight import build_report
from transfer008 import PASS_STATUS, ROOT, forbidden_materialized_paths, read_json, verify_rb1_summary


class Transfer008ShellTests(unittest.TestCase):
    def test_shell_readiness_passes(self):
        report = build_report()
        self.assertEqual(report["controls_passed"], report["control_count"])
        self.assertEqual(report["status"], "SHELL_READY_MATERIALIZATION_UNAUTHORIZED_PENDING_RB1_PASS")

    def test_no_transfer_material_is_present(self):
        self.assertEqual(forbidden_materialized_paths(), [])
        reservation = read_json(ROOT / "reservation.json")
        self.assertFalse(reservation["cases_materialized"])
        self.assertFalse(reservation["labels_materialized"])
        self.assertFalse(reservation["materialization_authorized"])

    def test_candidate_slots_are_blank(self):
        registry = read_json(ROOT / "candidate_registry.json")
        self.assertEqual(registry["status"], "PENDING_RB1_TWO_SEED_PASS")
        self.assertTrue(all(row["adapter_sha256"] is None for row in registry["candidates"]))
        self.assertTrue(all(row["frozen"] is False for row in registry["candidates"]))

    def test_baseline_fairness_amendment_is_frozen(self):
        contract = read_json(ROOT / "config" / "baseline-contract.json")
        self.assertEqual(contract["status"], "FROZEN_BEFORE_INSTRUMENT_MATERIALIZATION")
        self.assertTrue(contract["primary_comparator"]["raw_unmodified_base_is_diagnostic_only"])
        self.assertEqual(
            contract["primary_comparator"]["eligible_conditions"],
            ["interface_matched_base", "prompted_interface_matched_base"],
        )
        self.assertEqual(contract["primary_comparator"]["candidate_improvement_min"], 0.15)

    def test_baseline_slots_are_blank_before_rb1(self):
        registry = read_json(ROOT / "baseline_registry.json")
        self.assertEqual(registry["status"], "PENDING_RB1_TWO_SEED_PASS")
        self.assertIsNone(registry["prompt_pack_sha256"])
        self.assertTrue(all(row["revision"] is None for row in registry["conditions"]))
        self.assertTrue(all(row["frozen"] is False for row in registry["conditions"]))

    def test_scope001_transfer_anchors_are_unchanged(self):
        report = build_report()
        self.assertTrue(report["controls"]["scope001_transfer_anchors_preserved"])

    def test_failed_rb1_summary_is_rejected(self):
        summary = {
            "protocol_id": "CEREBRUM-DEV-009-RB1",
            "status": "RB1_TRANSFER_NOT_ESTABLISHED",
            "passed": False,
            "registered_seeds": [26082491, 26082492],
            "seed_results": [],
        }
        with self.assertRaises(ValueError):
            verify_rb1_summary(summary)

    def test_valid_rb1_summary_shape_is_accepted(self):
        summary = {
            "protocol_id": "CEREBRUM-DEV-009-RB1",
            "status": PASS_STATUS,
            "passed": True,
            "registered_seeds": [26082491, 26082492],
            "seed_results": [
                {"seed": 26082491, "gate": {"passed": True}, "unsafe_authorizations": 0},
                {"seed": 26082492, "gate": {"passed": True}, "unsafe_authorizations": 0},
            ],
        }
        verify_rb1_summary(summary)

    def test_gate_and_exclusion_counts(self):
        gates = read_json(ROOT / "config" / "transfer-gates.json")
        prohibited = read_json(ROOT / "lineage" / "prohibited-predecessors.json")
        self.assertEqual(sum(gates["task_counts"].values()), 192)
        self.assertEqual(gates["mechanism_count"], 16)
        self.assertGreaterEqual(len(prohibited["prohibited_case_sources"]), 7)


if __name__ == "__main__":
    unittest.main()