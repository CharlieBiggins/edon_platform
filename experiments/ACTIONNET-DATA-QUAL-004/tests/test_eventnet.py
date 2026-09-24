import json
import sys
import unittest
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from actionnet_eventnet import (
    PIVOTAL_MECHANISMS,
    TASK_TYPES,
    TRAIN_RENDERERS,
    VALIDATION_RENDERER,
    compact_commutative_events,
    execute,
    generate,
    schedule_a,
)


class EventNetTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.generated = generate()

    def test_all_registered_controls_pass(self):
        failed = [name for name, passed in self.generated["controls"].items() if not passed]
        self.assertEqual(failed, [])

    def test_registered_counts_tasks_and_renderers(self):
        train = self.generated["datasets"]["train"]
        validation = self.generated["datasets"]["repair_validation"]
        self.assertEqual(len(train), 5040)
        self.assertEqual(len(validation), 420)
        self.assertEqual(len(self.generated["canonical_trajectories"]), 600)
        self.assertEqual(set(row["metadata"]["task_type"] for row in train), set(TASK_TYPES))
        self.assertEqual(set(row["metadata"]["selected_renderer"] for row in train), set(TRAIN_RENDERERS))
        self.assertEqual(set(row["metadata"]["selected_renderer"] for row in validation), {VALIDATION_RENDERER})

    def test_every_pivotal_mechanism_appears_in_both_splits(self):
        for split in ("train", "repair_validation"):
            mechanisms = self.generated["audits"][split]["mechanism_distribution"]
            self.assertTrue(set(PIVOTAL_MECHANISMS).issubset(mechanisms))

    def test_scheduler_receipts_are_canonical(self):
        for trajectory in self.generated["canonical_trajectories"]:
            expected = [event["event_id"] for event in schedule_a(trajectory["submitted_events"])]
            self.assertEqual(trajectory["execution_receipt"]["ordered_event_ids"], expected)
            self.assertGreaterEqual(len(expected), 4)

    def test_transition_and_queue_targets_match_oracle(self):
        trajectories = {row["trajectory_id"]: row for row in self.generated["canonical_trajectories"]}
        for row in self.generated["datasets"]["train"]:
            task = row["metadata"]["task_type"]
            if task not in {"TRANSITION", "QUEUE_TRACE"}:
                continue
            trajectory = trajectories[row["metadata"]["trajectory_id"]]
            if task == "TRANSITION":
                self.assertEqual(row["target"]["post_state"], trajectory["final_state"])
                self.assertEqual(row["target"]["execution_receipt"], trajectory["execution_receipt"])
            else:
                for key, value in trajectory["execution_receipt"].items():
                    self.assertEqual(row["target"][key], value)
            self.assertFalse(row["target"]["binding_authority"])

    def test_safe_event_compaction_preserves_semantics(self):
        checks = 0
        for trajectory in self.generated["canonical_trajectories"]:
            compacted = compact_commutative_events(trajectory["submitted_events"])
            if len(compacted) == len(trajectory["submitted_events"]):
                continue
            outcome, state, _, _, _ = execute(trajectory["initial_state"], compacted)
            self.assertEqual(outcome, trajectory["outcome"])
            self.assertEqual(state, trajectory["final_state"])
            checks += 1
        self.assertGreater(checks, 0)

    def test_inputs_exclude_audit_metadata_and_labels(self):
        forbidden = {
            "case_id",
            "trajectory_id",
            "counterfactual_pair_id",
            "institution_lineage",
            "generator_lineage",
            "pair_class",
            "variant",
            "intervention_family",
            "target",
            "oracle",
            "semantic_state",
            "failed_conditions",
        }
        for row in self.generated["datasets"]["train"] + self.generated["datasets"]["repair_validation"]:
            self.assertEqual(set(row["input"]), {"observation", "query"})
            text = json.dumps(row["input"], sort_keys=True)
            self.assertFalse(any(f'"{key}"' in text for key in forbidden))

    def test_pivotal_weights_and_effective_decision_balance(self):
        train = self.generated["datasets"]["train"]
        pivotal_pair_weights = Counter(
            row["metadata"]["sample_weight"]
            for row in train
            if row["metadata"]["task_type"] == "PAIR_CONTRAST" and row["metadata"]["pair_class"] == "PIVOTAL"
        )
        self.assertEqual(set(pivotal_pair_weights), {2.0})
        effective = self.generated["audits"]["train_records"]["effective_weighted_decisions"]
        self.assertLess(max(effective.values()) - min(effective.values()), 0.01)

    def test_generation_is_deterministic(self):
        self.assertEqual(self.generated, generate())


if __name__ == "__main__":
    unittest.main()