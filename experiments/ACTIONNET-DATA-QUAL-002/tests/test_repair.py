import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from actionnet_repair import canonical, generate
from run_campaign import observability_audit


class RepairTests(unittest.TestCase):
    def test_generation_is_deterministic(self):
        self.assertEqual(canonical(generate()["datasets"]), canonical(generate()["datasets"]))

    def test_observability_gates(self):
        generated = generate()
        audit = observability_audit(generated["datasets"], generated["public_labels"])
        self.assertEqual(sum(audit["id_free_conflicting_target_groups"].values()), 0)
        self.assertEqual(audit["invalid_targets_without_malformed_observation"], 0)
        self.assertTrue(audit["memo_event_values_visible"])
        self.assertTrue(audit["model_inputs_exclude_case_and_institution_ids"])

    def test_public_labels_remain_separate(self):
        generated = generate()
        self.assertTrue(all(set(row) == {"case_id", "input"} for row in generated["datasets"]["public_holdout"]))


if __name__ == "__main__":
    unittest.main()