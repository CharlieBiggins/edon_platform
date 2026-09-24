#!/usr/bin/env python3
from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from actionnet019 import CONDITIONS, generate  # noqa: E402


class ActionNet019Tests(unittest.TestCase):
    def test_controls_and_counts(self):
        generated = generate()
        self.assertTrue(all(generated["controls"].values()))
        self.assertEqual(len(generated["dataset"]), 160)
        self.assertEqual(set(CONDITIONS), {
            row["metadata"]["diagnostic_condition"] for row in generated["dataset"]
        })

    def test_generation_is_deterministic(self):
        self.assertEqual(generate(), generate())


if __name__ == "__main__":
    unittest.main()