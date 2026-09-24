"""Regression tests for CEREBRUM-MATURE-PLATFORM-SPEC-001."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PREFLIGHT = (
    ROOT
    / "governance"
    / "architecture"
    / "CEREBRUM-MATURE-PLATFORM-SPEC-001"
    / "preflight.py"
)


class MaturePlatformSpecificationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        spec = importlib.util.spec_from_file_location("mature_platform_preflight", PREFLIGHT)
        if spec is None or spec.loader is None:
            raise RuntimeError("could not load mature-platform preflight")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        cls.result = module.verify()

    def test_frozen_specification_and_dependency(self) -> None:
        self.assertEqual(self.result["status"], "PASS")
        self.assertEqual(self.result["specification_id"], "CEREBRUM-MATURE-PLATFORM-SPEC-001")
        self.assertEqual(self.result["architecture_dependency"], "CEREBRUM-PLATFORM-VISION-002")

    def test_specification_and_schema_counts(self) -> None:
        self.assertEqual(self.result["canonical_specifications"], 11)
        self.assertEqual(self.result["new_schemas"], 6)

    def test_no_binding_authority_claim(self) -> None:
        self.assertIs(self.result["binding_authority"], False)


if __name__ == "__main__":
    unittest.main()