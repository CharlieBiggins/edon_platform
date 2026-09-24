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
        self.assertEqual(len(train), 8064)
        self.assertEqual(len(validation), 1344)
        self.assertEqual(len(self.generated["canonical_trajectories"]), 1152)
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
                self.assertEqual(
                    set(row["target"]),
                    {"post_state", "semantic_state", "decision", "failed_conditions", "binding_authority"},
                )
            else:
                receipt = trajectory["execution_receipt"]
                self.assertEqual(row["target"]["ordered_event_ids"], receipt["ordered_event_ids"])
                self.assertEqual(row["target"]["executed_event_ids"], receipt["executed_event_ids"])
                self.assertEqual(row["target"]["deferred_event_ids"], receipt["deferred_event_ids"])
                self.assertEqual(row["target"]["final_state"], trajectory["final_state"])
                self.assertNotIn("final_state_sha256", row["target"])
                self.assertTrue(all("state_sha256" not in step for step in row["target"]["step_semantics"]))
            self.assertFalse(row["target"]["binding_authority"])

    def test_fresh_families_and_validation_renderer(self):
        train = self.generated["datasets"]["train"]
        validation = self.generated["datasets"]["repair_validation"]
        self.assertEqual({row["metadata"]["semantic_family"] for row in train}, set(range(110, 126)))
        self.assertEqual({row["metadata"]["semantic_family"] for row in validation}, set(range(140, 148)))
        self.assertEqual({row["metadata"]["selected_renderer"] for row in validation}, {"REVIEW_MEMORANDUM"})
        self.assertEqual(self.generated["audits"]["actionnet_005_case_overlap"], 0)
        self.assertEqual(self.generated["audits"]["actionnet_005_prompt_overlap"], 0)

    def test_unresolved_appeal_focus_is_balanced_and_diverse(self):
        audits = self.generated["audits"]
        self.assertGreaterEqual(audits["appeal_train_certificate_count"], 400)
        self.assertGreaterEqual(audits["appeal_validation_certificate_count"], 60)
        self.assertEqual(audits["appeal_validation_decisions"], {"ALLOW": 32, "CONTESTED": 32})
        self.assertEqual(
            audits["appeal_resolution_times"],
            {"train": [6, 8, 9, 11, 12, 14], "repair_validation": [6, 8, 9, 11, 12, 14]},
        )

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
        self.assertEqual(set(pivotal_pair_weights), {3.0, 4.5})
        task_weight_sums = Counter()
        for row in train:
            task_weight_sums[row["metadata"]["task_type"]] += row["metadata"]["sample_weight"]
        self.assertGreater(task_weight_sums["TRANSITION"], task_weight_sums["CERTIFICATE"])
        self.assertGreater(task_weight_sums["QUEUE_TRACE"], task_weight_sums["CERTIFICATE"])
        effective = self.generated["audits"]["train_records"]["effective_weighted_decisions"]
        self.assertLess(max(effective.values()) - min(effective.values()), 0.01)

    def test_generation_is_deterministic(self):
        self.assertEqual(self.generated, generate())


if __name__ == "__main__":
    unittest.main()