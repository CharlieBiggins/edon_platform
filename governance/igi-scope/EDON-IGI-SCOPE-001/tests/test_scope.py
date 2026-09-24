import importlib.util
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("edon_igi_scope_001_preflight", ROOT / "preflight.py")
assert SPEC and SPEC.loader
PREFLIGHT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(PREFLIGHT)


class Scope001Tests(unittest.TestCase):
    def test_frozen_scope_definition_is_valid_without_claiming_igi(self):
        report = PREFLIGHT.build_report()
        self.assertEqual(report["status"], "FROZEN_SCOPE_DEFINITION_VALID_NO_IGI_RESULT", report)
        self.assertEqual(report["controls_passed"], report["control_count"])
        self.assertFalse(report["scope_generality_established"])
        self.assertFalse(report["universal_igi_established"])
        self.assertFalse(report["external_pilot_authorized"])
        self.assertFalse(report["production_authorized"])
        self.assertFalse(report["binding_authority"])


if __name__ == "__main__":
    unittest.main()