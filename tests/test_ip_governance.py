import importlib.util
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VALIDATOR_PATH = ROOT / "scripts" / "release" / "validate_ip_governance.py"


def load_validator():
    spec = importlib.util.spec_from_file_location("validate_ip_governance", VALIDATOR_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load IP-governance validator")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class IPGovernanceTests(unittest.TestCase):
    def test_public_ip_governance_fails_closed(self):
        report = load_validator().validate(ROOT)
        self.assertEqual(report["status"], "PASS", report["errors"])
        self.assertEqual(report["candidate_family_count"], 4)
        self.assertEqual(report["trademark_candidate_count"], 4)
        self.assertEqual(report["trade_secret_category_count"], 6)
        self.assertEqual(report["controls_passed"], report["control_count"])

    def test_no_candidate_is_recorded_as_filed_or_patent_pending(self):
        record = json.loads(
            (ROOT / "governance" / "ip" / "candidate-families.json").read_text(encoding="utf-8")
        )
        for family in record["candidate_families"]:
            with self.subTest(family=family["id"]):
                self.assertEqual(family["filing_status"], "NOT_FILED")
                self.assertFalse(family["patent_pending"])
                self.assertFalse(family["patentability_determined"])

    def test_release_review_template_is_not_authorized(self):
        review = json.loads(
            (ROOT / "governance" / "ip" / "release-review.template.json").read_text(encoding="utf-8")
        )
        self.assertFalse(review["release_authorized"])
        self.assertTrue(all(value is False for value in review["checks"].values()))


if __name__ == "__main__":
    unittest.main()