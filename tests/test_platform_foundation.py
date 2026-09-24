"""Regression tests for the draft Platform Foundation and AWS profile."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load_verify(name: str, relative: str):
    path = ROOT / relative
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"could not load {name}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.verify()


class PlatformFoundationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.foundation = load_verify(
            "platform_foundation_preflight",
            "governance/architecture/CEREBRUM-PLATFORM-FOUNDATION-001/preflight.py",
        )
        cls.aws = load_verify(
            "aws_deployment_profile_preflight",
            "governance/architecture/CEREBRUM-AWS-DEPLOYMENT-PROFILE-001/preflight.py",
        )

    def test_foundation_is_draft_and_unfrozen(self) -> None:
        self.assertEqual(self.foundation["status"], "PASS")
        self.assertEqual(self.foundation["freeze_gates"], 14)
        self.assertIs(self.foundation["hash_frozen"], False)

    def test_aws_profile_depends_on_foundation(self) -> None:
        self.assertEqual(self.aws["status"], "PASS")
        self.assertEqual(
            self.aws["foundation_dependency"], "CEREBRUM-PLATFORM-FOUNDATION-001"
        )
        self.assertEqual(self.aws["qualification_gates"], 12)

    def test_neither_record_grants_binding_authority(self) -> None:
        self.assertIs(self.foundation["binding_authority"], False)
        self.assertIs(self.aws["binding_authority"], False)


if __name__ == "__main__":
    unittest.main()