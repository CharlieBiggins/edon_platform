import json
import sys
import unittest
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from actionnet_multiview import TASK_TYPES, TRAIN_RENDERERS, VALIDATION_RENDERER, generate


class MultiViewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.generated = generate()

    def test_all_registered_controls_pass(self):
        failed = [name for name, passed in self.generated["controls"].items() if not passed]
        self.assertEqual(failed, [])

    def test_registered_counts_and_tasks(self):
        train = self.generated["datasets"]["train"]
        validation = self.generated["datasets"]["repair_validation"]
        self.assertEqual(len(train), 3600)
        self.assertEqual(len(validation), 300)
        self.assertEqual(set(row["metadata"]["task_type"] for row in train), set(TASK_TYPES))
        self.assertEqual(set(row["metadata"]["selected_renderer"] for row in train), set(TRAIN_RENDERERS))
        self.assertEqual(set(row["metadata"]["selected_renderer"] for row in validation), {VALIDATION_RENDERER})

    def test_transition_targets_match_canonical_post_state(self):
        trajectories = {row["trajectory_id"]: row for row in self.generated["canonical_trajectories"]}
        for row in self.generated["datasets"]["train"]:
            if row["metadata"]["task_type"] != "TRANSITION":
                continue
            trajectory = trajectories[row["metadata"]["trajectory_id"]]
            self.assertEqual(row["target"]["decision"], trajectory["outcome"]["decision"])
            self.assertEqual(row["target"]["semantic_state"], trajectory["outcome"]["semantic_state"])
            self.assertFalse(row["target"]["binding_authority"])

    def test_inputs_exclude_audit_metadata(self):
        forbidden = {"case_id", "trajectory_id", "counterfactual_pair_id", "institution_lineage", "generator_lineage", "pair_class", "variant", "intervention_family", "target", "oracle"}
        for row in self.generated["datasets"]["train"] + self.generated["datasets"]["repair_validation"]:
            self.assertEqual(set(row["input"]), {"observation", "query"})
            text = json.dumps(row["input"], sort_keys=True)
            self.assertFalse(any(key in text for key in forbidden))

    def test_pivotal_weighting_and_decision_balance(self):
        train = self.generated["datasets"]["train"]
        pair_weights = Counter(row["metadata"]["sample_weight"] for row in train if row["metadata"]["task_type"] == "PAIR_CONTRAST" and row["metadata"]["pair_class"] == "PIVOTAL")
        self.assertEqual(set(pair_weights), {2.0})
        effective = self.generated["audits"]["train_records"]["effective_weighted_decisions"]
        self.assertLess(max(effective.values()) - min(effective.values()), 0.01)

    def test_generation_is_deterministic(self):
        self.assertEqual(self.generated, generate())


if __name__ == "__main__":
    unittest.main()