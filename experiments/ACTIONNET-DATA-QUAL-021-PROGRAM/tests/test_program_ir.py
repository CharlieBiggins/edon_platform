from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from actionnet021 import make_split, renderer_lineage  # noqa: E402
from program_ir import parse_program_a, parse_program_b, verify_program  # noqa: E402


class ProgramIRTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        rows, trajectories, *_ = make_split("unit", 17, (1500,), ("unit",), renderer_lineage())
        cls.row = rows[0]
        cls.trajectory = trajectories[0]

    def test_oracle_program_parses_and_executes_twice(self):
        text = self.row["target"]["program"]
        self.assertEqual(parse_program_a(text), parse_program_b(text))
        source = self.row["input"]["program_source"]
        result = verify_program(
            text,
            source["initial_state"],
            source["submitted_events"],
            self.row["target"]["final_state"],
            self.row["target"]["certificate"],
        )
        self.assertTrue(result["accepted_by_verifier"])
        self.assertTrue(result["program_exact"])

    def test_wrong_order_is_rejected(self):
        lines = self.row["target"]["program"].splitlines()
        step_indexes = [index for index, line in enumerate(lines) if line.startswith("STEP ")]
        lines[step_indexes[0]], lines[step_indexes[1]] = lines[step_indexes[1]], lines[step_indexes[0]]
        source = self.row["input"]["program_source"]
        result = verify_program(
            "\n".join(lines),
            source["initial_state"],
            source["submitted_events"],
            self.row["target"]["final_state"],
            self.row["target"]["certificate"],
        )
        self.assertFalse(result["event_order_exact"])
        self.assertFalse(result["accepted_by_verifier"])


if __name__ == "__main__":
    unittest.main()