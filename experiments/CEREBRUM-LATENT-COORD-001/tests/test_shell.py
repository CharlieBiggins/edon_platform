#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from preflight import build_report, forbidden_materialized_paths


class LatentCoordinationShellTests(unittest.TestCase):
    def test_all_shell_controls_pass(self):
        report = build_report()
        self.assertEqual(
            report["status"], "SHELL_READY_INSTRUMENT_AND_CANDIDATE_UNMATERIALIZED"
        )
        self.assertEqual(report["controls_passed"], report["control_count"])

    def test_protected_material_and_candidate_are_absent(self):
        reservation = json.loads((ROOT / "reservation.json").read_text(encoding="utf-8"))
        self.assertEqual(forbidden_materialized_paths(), [])
        self.assertFalse(reservation["candidate"]["frozen"])
        self.assertFalse(reservation["cases_materialized"])
        self.assertFalse(reservation["labels_materialized"])
        self.assertFalse(reservation["score_authorized"])

    def test_pivotal_pairs_and_modes_are_balanced(self):
        gates = json.loads((ROOT / "config" / "gates.json").read_text(encoding="utf-8"))
        self.assertEqual(sum(gates["task_counts"].values()), 480)
        self.assertEqual(sum(gates["pair_counts"].values()), 240)
        self.assertEqual(set(gates["coordination_mode_counts"].values()), {60})
        self.assertEqual(gates["candidate_seeds_required"], 2)

    def test_output_is_nonbinding_and_nonexecuting(self):
        schema = json.loads(
            (
                ROOT.parents[1]
                / "schemas"
                / "cerebrum"
                / "coordination-hypothesis.schema.json"
            ).read_text(encoding="utf-8")
        )
        self.assertIs(schema["properties"]["binding_authority"]["const"], False)
        self.assertIs(schema["properties"]["executed"]["const"], False)


if __name__ == "__main__":
    unittest.main()