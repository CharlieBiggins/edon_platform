import json
import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dev010_common import CONFIG, read_jsonl
from prepare_data import SYSTEM_PROMPT, prepare


class Dev010Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest = prepare()
        cls.train = read_jsonl(ROOT / "prepared" / "train.jsonl")
        cls.validation = read_jsonl(ROOT / "prepared" / "validation-192.jsonl")

    def test_registered_counts(self):
        self.assertEqual(len(self.train), 4032)
        self.assertEqual(len(self.validation), 192)

    def test_auxiliary_tasks_are_training_only(self):
        self.assertIn("QUEUE_ORDER", {row["task_type"] for row in self.train})
        self.assertIn("QUEUE_PARTITION", {row["task_type"] for row in self.train})
        self.assertEqual({row["task_type"] for row in self.validation}, {"CERTIFICATE", "TRANSITION", "QUEUE_TRACE", "PAIR_CONTRAST"})

    def test_prompt_states_integrity_and_appeal_clock_contracts(self):
        self.assertIn("exactly once", SYSTEM_PROMPT)
        self.assertIn("disjoint exhaustive order-preserving", SYSTEM_PROMPT)
        self.assertIn("appeal as resolved", SYSTEM_PROMPT)

    def test_train_validation_are_disjoint(self):
        self.assertFalse({row["case_id"] for row in self.train} & {row["case_id"] for row in self.validation})
        self.assertFalse({row["counterfactual_pair_id"] for row in self.train} & {row["counterfactual_pair_id"] for row in self.validation})

    def test_config_freezes_revision_and_two_seeds(self):
        config = json.loads(CONFIG.read_text(encoding="utf-8"))
        self.assertEqual(config["registered_seeds"], [26090401, 26090402])
        self.assertEqual(config["model_revision"], "cdbee75f17c01a7cc42f958dc650907174af0554")

    def test_preflight_passes(self):
        completed = subprocess.run([sys.executable, "preflight.py"], cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)


if __name__ == "__main__":
    unittest.main()