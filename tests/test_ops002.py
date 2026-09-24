import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from edon.evaluation import run_ops002


class Ops002Tests(unittest.TestCase):
    def test_closed_loop_integration_gate(self):
        report = run_ops002()
        self.assertEqual(report["status"], "PASS", report)
        self.assertEqual(report["checks_passed"], 10)
        self.assertEqual(report["check_count"], 10)
        self.assertTrue(all(report["gates"].values()))


if __name__ == "__main__":
    unittest.main()