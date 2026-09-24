import importlib.util
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("feasibility_run", ROOT / "run.py")
run = importlib.util.module_from_spec(spec); spec.loader.exec_module(run)


class FeasibilityTests(unittest.TestCase):
    def test_prepare_reference_and_limited_baseline(self):
        with tempfile.TemporaryDirectory(dir=".") as tmp:
            target = Path(tmp) / "run"; report = run.prepare(target)
            self.assertEqual(report["episode_count"], 12)
            reference = run.execute(target, "reference"); baseline = run.execute(target, "baseline")
            self.assertEqual(reference["episodes_completed"], 12)
            self.assertEqual(reference["kernel_rejections"], 3)
            self.assertLess(baseline["episodes_completed"], 12)
            self.assertEqual(reference["unsafe_proposals"], 0)

    def test_no_authority(self):
        self.assertFalse(run.preflight()["binding_authority"])


if __name__ == "__main__": unittest.main()