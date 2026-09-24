import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from audit_transfer007 import audit
from canonicalize import compile_prediction, digest, valid_raw
from cerebrum_eventnet_data import ACTIONNET, REGISTERED_CONDITION_COUNTS, prepare, read_jsonl
from evaluate import score
from rules_baseline import predict_input


class EventNetRepairProtocolTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest = prepare()
        cls.validation_source = read_jsonl(ACTIONNET / "dataset" / "repair_validation.jsonl")
        cls.expected = read_jsonl(ROOT / "prepared" / "fresh-validation-all.jsonl")
        prepared_by_id = {row["case_id"]: row for row in cls.expected}
        cls.predictions = []
        for row in cls.validation_source:
            task = row["metadata"]["task_type"]
            parsed = predict_input(row["input"])
            expected = prepared_by_id[row["case_id"]]
            cls.predictions.append({
                "case_id": row["case_id"],
                "task_type": task,
                "parsed": parsed,
                "compiled": compile_prediction(task, expected["compiler_input"], parsed),
                "confidence": 1.0,
                "hit_generation_limit": False,
            })
        cls.rules = score(cls.predictions, cls.expected, "transparent_rules", None)

    def test_registered_condition_count(self):
        self.assertEqual(
            {name: row["records"] for name, row in self.manifest["conditions"].items()},
            REGISTERED_CONDITION_COUNTS,
        )

    def test_fresh_validation_counts_tasks_renderer_and_families(self):
        self.assertEqual(len(self.expected), 1344)
        self.assertEqual(
            {task: sum(row["task_type"] == task for row in self.expected) for task in {row["task_type"] for row in self.expected}},
            {"CERTIFICATE": 384, "TRANSITION": 384, "QUEUE_TRACE": 384, "PAIR_CONTRAST": 192},
        )
        self.assertEqual({row["selected_renderer"] for row in self.expected}, {"DEPENDENCY_GRAPH_PACKET"})
        self.assertEqual({row["semantic_family"] for row in self.expected}, set(range(340, 346)))
        self.assertEqual({row["generator_profile"] for row in self.expected}, {"GRAPH"})
        training = read_jsonl(ROOT / "prepared" / "train-execution-repair.jsonl")
        self.assertEqual({row["generator_profile"] for row in training}, {"LEDGER", "MATRIX"})

    def test_model_prompts_exclude_compiler_inputs_and_audit_metadata(self):
        source_rows = read_jsonl(ACTIONNET / "dataset" / "train.jsonl") + self.validation_source
        source = {row["case_id"]: row for row in source_rows}
        prepared = read_jsonl(ROOT / "prepared" / "train-execution-repair.jsonl") + self.expected
        for row in prepared:
            metadata = source[row["case_id"]]["metadata"]
            forbidden = [
                row["case_id"], metadata.get("trajectory_id"), metadata.get("counterfactual_pair_id"),
                metadata.get("institution_lineage"), metadata.get("generator_lineage"),
                metadata.get("source_lineage"), metadata.get("authority_graph_lineage"),
                metadata.get("workflow_graph_lineage"),
                source[row["case_id"]]["input"]["observation"].get("renderer_lineage"),
            ]
            self.assertFalse(any(value and str(value) in row["prompt"] for value in forbidden))
            self.assertNotIn("compiler_input", row["prompt"])
            self.assertFalse(json.loads(row["completion"])["binding_authority"])

    def test_raw_targets_are_compact_and_hash_free(self):
        rows = read_jsonl(ROOT / "prepared" / "train-execution-repair.jsonl") + self.expected
        for row in rows:
            value = json.loads(row["completion"])
            self.assertTrue(valid_raw(row["task_type"], value))
            self.assertNotIn("sha256", json.dumps(value, sort_keys=True))

    def test_compiler_hashes_predicted_state_without_executing_events(self):
        row = next(item for item in self.expected if item["task_type"] == "TRANSITION")
        raw = json.loads(row["completion"])
        raw["post_state"] = {"model_predicted": True}
        compiled = compile_prediction("TRANSITION", row["compiler_input"], raw)
        self.assertEqual(compiled["final_state_sha256"], digest({"model_predicted": True}))
        self.assertEqual(compiled["post_state"], {"model_predicted": True})

    def test_rules_ceiling_exact_and_passes_all_checks(self):
        self.assertEqual(self.rules["certificate"]["decision_accuracy"], 1.0)
        self.assertEqual(self.rules["transition"]["exact_match"], 1.0)
        self.assertEqual(self.rules["queue_trace"]["exact_match"], 1.0)
        self.assertEqual(self.rules["pair_contrast"]["exact_match"], 1.0)
        self.assertEqual(
            self.rules["advancement_gate"]["checks_passed"],
            self.rules["advancement_gate"]["check_count"],
        )
        self.assertTrue(self.rules["advancement_gate"]["passed"])
        self.assertEqual(self.rules["queue_trace"]["deferred_events_exact"], 1.0)
        self.assertEqual(self.rules["pair_contrast"]["causal_event_change_paths_exact"], 1.0)
        self.assertEqual(self.rules["pair_contrast"]["changed_post_state_paths_exact"], 1.0)

    def test_context_and_generation_limits_are_preregistered(self):
        config = json.loads((ROOT / "configs" / "qwen3-4b-multigen-repair.json").read_text(encoding="utf-8"))
        self.assertEqual(config["max_length"], config["inference_max_input_tokens"])
        self.assertTrue(config["require_zero_training_truncation"])
        self.assertGreaterEqual(config["task_token_limits"]["TRANSITION"], 1536)
        self.assertGreaterEqual(config["task_token_limits"]["QUEUE_TRACE"], 1536)
        self.assertGreaterEqual(config["task_token_limits"]["PAIR_CONTRAST"], 2048)

    def test_transfer007_failure_audit_confirms_execution_scope(self):
        observed = json.loads(
            (ROOT / "evidence" / "transfer007-observed-result.json").read_text(encoding="utf-8")
        )
        result = audit(observed)
        self.assertEqual(result["status"], "EXECUTION_TRANSFER_FAILURE_CONFIRMED")
        self.assertEqual(result["checks_passed"], result["check_count"])

    def test_launcher_has_resume_and_no_public_stage(self):
        source = (ROOT / "lightning_launcher.py").read_text(encoding="utf-8")
        self.assertIn("latest_checkpoint", source)
        self.assertIn("resuming training from", source)
        self.assertIn("fresh-validation-all.jsonl", source)
        self.assertNotIn('subparsers.add_parser("public")', source)
        self.assertNotIn('subparsers.add_parser("protected")', source)

    def test_preparation_is_deterministic(self):
        self.assertEqual(self.manifest["prepared_hashes"], prepare()["prepared_hashes"])


if __name__ == "__main__":
    unittest.main()