"""Regression tests for CEREBRUM-PLATFORM-VISION-001."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PREFLIGHT = (
    ROOT
    / "governance"
    / "architecture"
    / "CEREBRUM-PLATFORM-VISION-002"
    / "preflight.py"
)


class PlatformVisionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        spec = importlib.util.spec_from_file_location("platform_vision_chain_preflight", PREFLIGHT)
        if spec is None or spec.loader is None:
            raise RuntimeError("could not load platform-vision preflight")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        cls.result = module.verify()

    def test_frozen_record_and_inventory(self) -> None:
        self.assertEqual(self.result["status"], "PASS")
        self.assertEqual(self.result["predecessor"], "CEREBRUM-PLATFORM-VISION-001")
        self.assertEqual(self.result["predecessor_inventory_files"], 23)

    def test_canonical_contract_count(self) -> None:
        self.assertEqual(self.result["predecessor_canonical_specifications"], 6)

    def test_no_binding_authority_claim(self) -> None:
        self.assertIs(self.result["binding_authority"], False)


if __name__ == "__main__":
    unittest.main()