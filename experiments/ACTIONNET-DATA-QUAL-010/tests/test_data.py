import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from actionnet010 import SCORED_TASKS, TRAIN_TASKS, VALIDATION_RENDERER, generate


class ActionNet010Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.generated = generate()

    def test_all_controls_pass(self):
        self.assertEqual([name for name, passed in self.generated["controls"].items() if not passed], [])

    def test_registered_counts(self):
        self.assertEqual(len(self.generated["datasets"]["train"]), 4032)
        self.assertEqual(len(self.generated["datasets"]["repair_validation"]), 192)

    def test_tasks(self):
        train = {row["metadata"]["task_type"] for row in self.generated["datasets"]["train"]}
        validation = {row["metadata"]["task_type"] for row in self.generated["datasets"]["repair_validation"]}
        self.assertEqual(train, set(TRAIN_TASKS))
        self.assertEqual(validation, set(SCORED_TASKS))

    def test_heldout_renderer(self):
        validation = self.generated["datasets"]["repair_validation"]
        self.assertEqual({row["metadata"]["selected_renderer"] for row in validation}, {VALIDATION_RENDERER})

    def test_generation_is_deterministic(self):
        self.assertEqual(self.generated, generate())


if __name__ == "__main__":
    unittest.main()