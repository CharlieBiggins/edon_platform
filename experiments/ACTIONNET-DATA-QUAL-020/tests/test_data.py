from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from actionnet020 import FIDELITY_CONDITION, REPRESENTATIONS, canonical, generate  # noqa: E402


class ActionNet020Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.generated = generate()

    def test_controls_and_counts(self):
        self.assertTrue(all(self.generated["controls"].values()))
        self.assertEqual(len(self.generated["calibration"]), 384)
        self.assertEqual(len(self.generated["heldout_validation"]), 384)

    def test_generation_is_deterministic(self):
        self.assertEqual(canonical(self.generated), canonical(generate()))

    def test_each_scenario_has_five_formats_and_fidelity(self):
        expected = set(REPRESENTATIONS) | {FIDELITY_CONDITION}
        for split in ("calibration", "heldout_validation"):
            groups = {}
            for row in self.generated[split]:
                groups.setdefault(row["metadata"]["calibration_scenario_id"], []).append(row)
            self.assertEqual(len(groups), 64)
            for rows in groups.values():
                self.assertEqual({row["metadata"]["calibration_condition"] for row in rows}, expected)

    def test_representation_inputs_have_one_source(self):
        rows = [
            row for row in self.generated["calibration"]
            if row["metadata"]["calibration_arm"] == "REPRESENTATION"
        ]
        for row in rows:
            content = row["input"]["observation"]["content"]
            self.assertNotIn("raw_observation", content)
            self.assertNotIn("predecision_state", content)
            self.assertNotIn("GOLD", content.upper())


if __name__ == "__main__":
    unittest.main()
