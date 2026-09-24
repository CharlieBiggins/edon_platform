import json
import sys
import unittest
from datetime import date
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from actionnet_multidomain import DOMAIN_PACKS, NEW_PIVOTAL_MECHANISMS, PIVOTAL_MECHANISMS, generate
from expert_router import build_review_queue, route_item
from feedback_pipeline import classify_feedback_event
from governance import evaluate_training_gate


class MultiDomainTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.generated = generate()

    def test_all_registered_controls_pass(self):
        self.assertEqual([name for name, passed in self.generated["controls"].items() if not passed], [])

    def test_registered_counts(self):
        self.assertEqual(len(DOMAIN_PACKS), 24)
        self.assertEqual(len(PIVOTAL_MECHANISMS), 20)
        self.assertEqual(len(self.generated["datasets"]["authoring_candidates"]), 4032)
        self.assertEqual(len(self.generated["datasets"]["heldout_authoring_validation"]), 1008)
        self.assertEqual(len(self.generated["canonical_trajectories"]), 576)
        self.assertEqual(len(self.generated["counterfactual_pairs"]), 288)

    def test_every_domain_and_registered_mechanism_is_materialized(self):
        audit = self.generated["audits"]["train"]
        self.assertEqual(set(audit["domain_distribution"]), {item["domain_id"] for item in DOMAIN_PACKS})
        for item in DOMAIN_PACKS:
            for mechanism in item["mechanisms"]:
                self.assertGreater(audit["domain_mechanism_distribution"][f"{item['domain_id']}:{mechanism}"], 0)

    def test_new_mechanisms_are_pivotal(self):
        pairs = self.generated["counterfactual_pairs"]
        for mechanism in NEW_PIVOTAL_MECHANISMS:
            matching = [pair for pair in pairs if pair["intervention_family"] == mechanism]
            self.assertGreater(len(matching), 0)
            self.assertTrue(all(pair["base"]["outcome"]["decision"] != pair["comparison"]["outcome"]["decision"] for pair in matching))

    def test_candidates_are_not_training_eligible(self):
        for row in self.generated["datasets"]["authoring_candidates"] + self.generated["datasets"]["heldout_authoring_validation"]:
            self.assertFalse(row["metadata"]["training_eligible"])
            self.assertEqual(row["metadata"]["expert_review_status"], "PENDING")
        for trajectory in self.generated["canonical_trajectories"]:
            self.assertFalse(trajectory["governance"]["training_eligible"])
            self.assertFalse(trajectory["governance"]["source_grounded"])

    def test_review_queue_is_pair_level_and_risk_aware(self):
        queue = build_review_queue(self.generated["counterfactual_pairs"])
        self.assertEqual(len(queue), 288)
        self.assertTrue(all(not item["training_eligible"] for item in queue))
        critical = [item for item in queue if item["risk_tier"] == "critical"]
        self.assertTrue(critical)
        self.assertTrue(all(item["independent_reviews_required"] == 2 for item in critical))
        self.assertTrue(all(item["adjudicator_required"] for item in critical))

    def test_router_enforces_verification_and_self_review(self):
        item = build_review_queue(self.generated["counterfactual_pairs"])[0]
        good = {
            "expert_id": "expert-a",
            "affiliation_id": "affiliation-a",
            "profile_status": "VERIFIED",
            "calibration_score": 0.95,
            "credential_expires_on": "2030-01-01",
            "verified_domains": [item["domain_id"]],
            "verified_specialties": [item["required_specialties"][0]],
            "verified_jurisdictions": [item["jurisdiction"]],
            "conflict_attestation_current": True,
            "completed_reviews": 40,
        }
        self_review = {**good, "expert_id": "expert-b", "affiliation_id": "affiliation-b", "authored_candidate_ids": [item["candidate_pair_id"]]}
        result = route_item(item, [self_review, good], as_of=date(2026, 8, 19))
        self.assertEqual(result["assigned_experts"][0]["expert_id"], "expert-a")
        rejected = {row["expert_id"]: row["reasons"] for row in result["rejected_experts"]}
        self.assertIn("SELF_REVIEW_PROHIBITED", rejected["expert-b"])

    def test_router_requires_independent_affiliations(self):
        item = build_review_queue(self.generated["counterfactual_pairs"])[0]
        item["independent_reviews_required"] = 2
        base = {
            "profile_status": "VERIFIED",
            "calibration_score": 0.95,
            "credential_expires_on": "2030-01-01",
            "verified_domains": [item["domain_id"]],
            "verified_specialties": [item["required_specialties"][0]],
            "verified_jurisdictions": [item["jurisdiction"]],
            "conflict_attestation_current": True,
        }
        profiles = [
            {**base, "expert_id": "expert-a", "affiliation_id": "same-org"},
            {**base, "expert_id": "expert-b", "affiliation_id": "same-org"},
        ]
        result = route_item(item, profiles, as_of=date(2026, 8, 19))
        self.assertEqual(result["routing_status"], "INSUFFICIENT_QUALIFIED_EXPERTS")
        self.assertEqual(len(result["assigned_experts"]), 1)

    def test_feedback_never_trains_directly(self):
        event = {
            "protected_case": False,
            "learning_mode": "global_deidentified",
            "human_correction": {"decision": "DENY"},
            "reason_codes": ["unsafe_allow"],
        }
        result = classify_feedback_event(event)
        self.assertEqual(result["classification"], "ACTIONNET_CANDIDATE")
        self.assertFalse(result["training_eligible"])
        event["protected_case"] = True
        self.assertEqual(classify_feedback_event(event)["classification"], "EXCLUDED")

    def test_training_gate_requires_every_release_control(self):
        passing = {
            "tenant_permission": "PASS",
            "source_permission": "PASS",
            "privacy_review": "PASS",
            "deidentification": "PASS",
            "expert_review": "PASS",
            "adjudication": "PASS",
            "duplicate_check": "PASS",
            "protected_case_excluded": "PASS",
            "dataset_freeze": "PASS",
            "release_approval": "PASS",
        }
        self.assertTrue(evaluate_training_gate(passing)["eligible"])
        passing["release_approval"] = "PENDING"
        result = evaluate_training_gate(passing)
        self.assertFalse(result["eligible"])
        self.assertIn("release_approval", result["failed_gates"])

    def test_contracts_and_registries_are_valid_json(self):
        paths = list((ROOT / "registry").glob("*.json")) + list((ROOT / "contracts").glob("*.json")) + list((ROOT / "expert").glob("*.schema.json"))
        self.assertGreaterEqual(len(paths), 8)
        for path in paths:
            json.loads(path.read_text(encoding="utf-8"))

    def test_generation_is_deterministic(self):
        self.assertEqual(self.generated, generate())


if __name__ == "__main__":
    unittest.main()