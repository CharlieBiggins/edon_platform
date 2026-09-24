import importlib.util
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("cerebrum_build_001_preflight", ROOT / "preflight.py")
assert SPEC and SPEC.loader
PREFLIGHT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(PREFLIGHT)


class BuildReadinessTests(unittest.TestCase):
    def test_engineering_shell_is_ready_without_claiming_a_model_result(self):
        report = PREFLIGHT.build_report()
        self.assertEqual(report["status"], "ENGINEERING_SHELL_READY_MODEL_EXECUTION_NOT_RUN", report)
        self.assertEqual(report["controls_passed"], report["control_count"])
        self.assertTrue(report["internal_shadow_authorized"])
        self.assertFalse(report["training_authorized"])
        self.assertFalse(report["external_pilot_authorized"])
        self.assertFalse(report["binding_authority"])


if __name__ == "__main__":
    unittest.main()