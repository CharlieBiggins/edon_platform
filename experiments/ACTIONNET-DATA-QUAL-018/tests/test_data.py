#!/usr/bin/env python3
from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from actionnet018 import generate  # noqa: E402


class ActionNet018Tests(unittest.TestCase):
    def test_registered_controls_pass(self):
        generated = generate()
        self.assertTrue(all(generated["controls"].values()))
        self.assertNotIn("train", generated["datasets"])
        self.assertEqual(len(generated["datasets"]["development_selection"]), 64)
        self.assertEqual(len(generated["datasets"]["untouched_confirmation"]), 192)

    def test_generation_is_deterministic(self):
        self.assertEqual(generate(), generate())


if __name__ == "__main__":
    unittest.main()