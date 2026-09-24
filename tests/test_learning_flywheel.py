import json
import sqlite3
import sys
import tempfile
import unittest
from contextlib import closing
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from edon.actionnet import (
    ActionNetPlatformStore,
    GovernedLearningNetwork,
    LearningNetworkError,
)
from edon.api.server import PlatformService, authorized
from edon.memory import EpisodicMemoryStore


SHA_A = "sha256:" + "a" * 64
SHA_B = "sha256:" + "b" * 64
SHA_C = "sha256:" + "c" * 64
SHA_D = "sha256:" + "d" * 64


class LearningFlywheelTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        root = Path(self.temp.name)
        self.local = ActionNetPlatformStore(root / "local-actionnet.sqlite3")
        self.network = GovernedLearningNetwork(
            root / "learning-network.sqlite3", self.local
        )

    def tearDown(self):
        self.temp.cleanup()

    def _local_experience(
        self,
        tenant_id="tenant-a",
        experience_id="experience-a",
        *,
        protected=False,
        eligible=True,
    ):
        self.local.register_mechanism(
            tenant_id,
            "queue-recovery",
            "1.0.0",
            "Queue recovery",
            "A queue recovery mechanism with a sufficiently detailed description.",
            {
                "preconditions": [],
                "state_transitions": [],
                "dependencies": [],
                "interventions": [],
                "failure_modes": [],
                "expected_outcomes": [],
            },
            created_by="author",
        )
        experience = self.local.record_experience(
            tenant_id,
            experience_id,
            "SIMULATOR",
            "HEALTHCARE",
            [{"mechanism_id": "queue-recovery", "version": "1.0.0"}],
            {"state": "RECOVERED"},
            {"path": ["queue", "reallocation", "outcome"]},
            evidence_grade="SYNTHETIC_VERIFIED",
            provenance={"generator": "fixture"},
            created_by="author",
            protected=protected,
        )
        if eligible and not protected:
            reviews = (
                ("domain", "ACTIONNET_DOMAIN_REVIEWER", "DOMAIN"),
                ("safety", "ACTIONNET_SAFETY_REVIEWER", "SAFETY"),
                ("lineage", "ACTIONNET_CUSTODIAN", "LINEAGE"),
                ("training", "ACTIONNET_RELEASE_MANAGER", "TRAINING"),
            )
            for reviewer, role, dimension in reviews:
                self.local.review_experience(
                    tenant_id,
                    f"review-{experience_id}-{dimension.lower()}",
                    experience_id,
                    reviewer,
                    role,
                    dimension,
                    "APPROVE",
                    "The bounded fixture satisfies the registered review dimension.",
                )
            self.local.record_overlap_check(
                tenant_id,
                experience_id,
                True,
                {"case_overlap": 0, "prompt_overlap": 0},
                actor_id="custodian",
            )
            self.local.approve_training_eligibility(
                tenant_id,
                experience_id,
                release_manager_id="release-manager",
                rationale="All required independent reviews and overlap controls passed.",
            )
        return experience

    @staticmethod
    def _normalized(**extra):
        return {
            "institution_type": "HEALTHCARE",
            "mechanism_families": ["QUEUE", "RESOURCE_ALLOCATION"],
            "trajectory_summary": {"initial": "CONGESTED", "final": "RECOVERED"},
            "outcome_summary": {"service_level": "RESTORED"},
            "generalized_pattern": {
                "pattern": "queue recovery follows governed resource reallocation"
            },
            "provenance_commitments": {
                "local_source_committed": True,
                "raw_source_centralized": False,
            },
            **extra,
        }

    def _promote(self, **overrides):
        values = {
            "tenant_id": "tenant-a",
            "request_id": "export-a",
            "experience_id": "experience-a",
            "global_record_id": "global-a",
            "normalized_experience": self._normalized(),
            "rights_basis": "SYNTHETIC",
            "rights_ref_sha256": SHA_A,
            "privacy_review_sha256": SHA_B,
            "source_review_sha256": SHA_C,
            "permitted_uses": ["TRAIN", "DEVELOPMENT"],
            "deidentification_attested": True,
            "raw_payload_included": False,
            "approved_by": "global-custodian",
        }
        values.update(overrides)
        return self.network.promote_local_experience(**values)

    def _release(self, record_id="global-a"):
        return self.network.create_global_training_release(
            "global-release-a",
            [record_id],
            "C1",
            protected_evaluation_reservation_sha256=SHA_D,
            dataset_overlap_report_sha256=SHA_C,
            release_manager_id="global-release-manager",
        )

    def test_memory_is_tenant_local_context_not_training(self):
        store = EpisodicMemoryStore(Path(self.temp.name) / "memory.sqlite3")
        memory = store.record_episode(
            "tenant-a",
            "memory-a",
            "hospital-a",
            "INSTITUTION_FACT",
            "The local transport provider closes at ten in the evening.",
            {"provider": "local-provider", "closing_hour": 22},
            occurred_at="2026-08-30T00:00:00+00:00",
            sensitivity="INTERNAL",
            actor_id="memory-writer",
            authorization_ref="memory-write-policy",
            source_event_ids=["event-a"],
        )
        self.assertEqual(memory["scope"], "INSTITUTION_LOCAL")
        self.assertEqual(memory["adaptation_mode"], "CONTEXT_ONLY")
        self.assertFalse(memory["training_eligible"])
        self.assertFalse(memory["weight_update_authorized"])

    def test_unreviewed_or_protected_local_experience_cannot_be_promoted(self):
        self._local_experience(eligible=False)
        with self.assertRaisesRegex(LearningNetworkError, "reviewed"):
            self._promote()

        self._local_experience(
            tenant_id="tenant-b", experience_id="protected-b", protected=True
        )
        with self.assertRaisesRegex(LearningNetworkError, "protected"):
            self._promote(
                tenant_id="tenant-b",
                request_id="export-b",
                experience_id="protected-b",
                global_record_id="global-b",
            )

    def test_global_abstraction_rejects_raw_identity_and_authority_fields(self):
        self._local_experience()
        with self.assertRaisesRegex(LearningNetworkError, "sensitive"):
            self._promote(
                normalized_experience=self._normalized(patient_name="not-allowed")
            )
        with self.assertRaisesRegex(LearningNetworkError, "raw local payload"):
            self._promote(raw_payload_included=True)

    def test_global_record_contains_commitment_not_tenant_identity(self):
        self._local_experience()
        record = self._promote()
        serialized = json.dumps(record, sort_keys=True)
        self.assertNotIn("tenant-a", serialized)
        self.assertNotIn("experience-a", serialized)
        self.assertTrue(record["deidentification_attested"])
        self.assertFalse(record["raw_payload_included"])
        self.assertTrue(record["training_eligible"])
        self.assertTrue(self.network.verify_audit_chain())

    def test_global_release_revalidates_local_eligibility(self):
        self._local_experience()
        self._promote()
        self.local.quarantine_experience(
            "tenant-a",
            "experience-a",
            "A subsequent custody review invalidated the local training eligibility.",
            actor_id="custodian",
        )
        with self.assertRaisesRegex(LearningNetworkError, "no longer satisfies"):
            self._release()

    def test_training_release_is_offline_and_does_not_authorize_weight_update(self):
        self._local_experience()
        self._promote()
        release = self._release()
        self.assertTrue(release["offline_training_only"])
        self.assertFalse(release["weight_update_authorized"])
        self.assertFalse(release["binding_authority"])

    def test_c1_versions_are_frozen_and_online_or_institution_updates_fail(self):
        self._local_experience()
        self._promote()
        self._release()
        with self.assertRaisesRegex(LearningNetworkError, "institution-specific"):
            self.network.register_c1_version(
                "C1-v1",
                "Qwen/Qwen3-4B",
                "c1-v1:test",
                "global-release-a",
                artifact_sha256=SHA_A,
                evaluation_sha256=SHA_B,
                license_id="test-license",
                safety_gate="PASS",
                performance_gate="PASS",
                transfer_gate="PASS",
                protected_evaluation_complete=True,
                created_by="release-manager",
                institution_specific_weight_updates_required=True,
            )
        with self.assertRaisesRegex(LearningNetworkError, "online production"):
            self.network.register_c1_version(
                "C1-v1",
                "Qwen/Qwen3-4B",
                "c1-v1:test",
                "global-release-a",
                artifact_sha256=SHA_A,
                evaluation_sha256=SHA_B,
                license_id="test-license",
                safety_gate="PASS",
                performance_gate="PASS",
                transfer_gate="PASS",
                protected_evaluation_complete=True,
                created_by="release-manager",
                online_weight_updates_allowed=True,
            )
        model = self.network.register_c1_version(
            "C1-v1",
            "Qwen/Qwen3-4B",
            "c1-v1:test",
            "global-release-a",
            artifact_sha256=SHA_A,
            adapter_sha256=SHA_C,
            evaluation_sha256=SHA_B,
            license_id="test-license",
            safety_gate="PASS",
            performance_gate="PASS",
            transfer_gate="PASS",
            protected_evaluation_complete=True,
            created_by="release-manager",
        )
        self.assertEqual(model["status"], "FROZEN_INTERNAL")
        self.assertEqual(model["deployment_status"], "NOT_DEPLOYED")
        self.assertFalse(model["online_weight_updates_allowed"])
        with self.assertRaises(sqlite3.DatabaseError):
            with closing(sqlite3.connect(self.network.path)) as connection:
                connection.execute(
                    "UPDATE c1_model_versions SET safety_gate = 'FAIL' WHERE model_id = 'C1-v1'"
                )

    def test_c1_dispositions_require_evidence_and_record_rollback_without_execution(self):
        self._local_experience()
        self._promote()
        self._release()
        self.network.register_c1_version(
            "C1-v1",
            "Qwen/Qwen3-4B",
            "c1-v1:test",
            "global-release-a",
            artifact_sha256=SHA_A,
            evaluation_sha256=SHA_B,
            license_id="test-license",
            safety_gate="PASS",
            performance_gate="PASS",
            transfer_gate="PASS",
            protected_evaluation_complete=True,
            created_by="release-manager",
        )
        shadow = self.network.record_c1_disposition(
            "C1-v1",
            "SHADOW_ELIGIBLE",
            evidence_ref_sha256=SHA_C,
            rationale="The protected safety, performance, and transfer gates all passed.",
            actor_id="release-manager",
        )
        self.assertFalse(shadow["operational_effect"])

        self.network.register_c1_version(
            "C1-v2",
            "Qwen/Qwen3-4B",
            "c1-v2:test",
            "global-release-a",
            artifact_sha256=SHA_D,
            evaluation_sha256=SHA_C,
            license_id="test-license",
            safety_gate="FAIL",
            performance_gate="PASS",
            transfer_gate="HOLD",
            protected_evaluation_complete=True,
            created_by="release-manager",
            predecessor_model_id="C1-v1",
        )
        with self.assertRaisesRegex(LearningNetworkError, "safety and performance"):
            self.network.record_c1_disposition(
                "C1-v2",
                "DEPLOYMENT_ELIGIBLE",
                evidence_ref_sha256=SHA_D,
                rationale="This disposition should fail because the safety gate failed.",
                actor_id="release-manager",
            )
        rollback = self.network.record_c1_disposition(
            "C1-v2",
            "ROLLBACK_REQUIRED",
            rollback_model_id="C1-v1",
            evidence_ref_sha256=SHA_D,
            rationale="The failed safety gate requires rollback to the previous frozen version.",
            actor_id="release-manager",
        )
        self.assertEqual(rollback["rollback_model_id"], "C1-v1")
        self.assertFalse(rollback["binding_authority"])

    def test_platform_exposes_separate_global_and_c1_roles(self):
        self.assertTrue(authorized("ACTIONNET_GLOBAL_CUSTODIAN", "actionnet_global"))
        self.assertFalse(authorized("ACTIONNET_AUTHOR", "actionnet_global"))
        self.assertTrue(authorized("C1_RELEASE_MANAGER", "c1_release"))
        with tempfile.TemporaryDirectory() as directory:
            service = PlatformService(directory)
            counts = service.status()["counts"]["actionnet_learning_network"]
            self.assertEqual(counts["global_records"], 0)
            self.assertEqual(counts["c1_versions"], 0)


if __name__ == "__main__":
    unittest.main()