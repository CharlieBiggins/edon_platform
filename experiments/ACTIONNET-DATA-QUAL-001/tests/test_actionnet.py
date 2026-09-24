import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from actionnet import canonical, evaluate_a, evaluate_b, generate, initial_state, family_config


class ActionNetTests(unittest.TestCase):
    def test_reference_engines_agree_on_base(self):
        state = initial_state(family_config(0), 0)
        self.assertEqual(evaluate_a(state), evaluate_b(state))

    def test_generation_is_deterministic_and_label_isolated(self):
        first = generate()
        second = generate()
        self.assertEqual(canonical(first["datasets"]), canonical(second["datasets"]))
        self.assertTrue(all("target" not in row for row in first["datasets"]["public_holdout"]))

    def test_registered_counts(self):
        result = generate()
        self.assertEqual({key: len(value) for key, value in result["datasets"].items()}, {"train": 480, "development": 120, "public_holdout": 120})


if __name__ == "__main__":
    unittest.main()