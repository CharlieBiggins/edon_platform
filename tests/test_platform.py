import json
import sqlite3
import sys
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from contextlib import closing
from copy import deepcopy
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from edon.actionnet import generate_actionnet
from edon.api.server import EDONHTTPServer, PlatformService
from edon.cerebrum import TrainingOrchestrator
from edon.compiler import compile_institution
from edon.gaps import discover_gaps
from edon.qualification import qualify_actionnet
from edon.registry import RegistryError, ReviewRegistry
from edon.runtime import InstitutionalRuntime, expected_facts
from edon.shadow import run_shadow_comparison


EXAMPLE = ROOT / "examples" / "hospital" / "compiler-input.json"


def promoted_registry(directory: Path) -> tuple[ReviewRegistry, dict]:
    report = compile_institution(EXAMPLE)
    registry = ReviewRegistry(directory / "registry.sqlite3")
    candidate_ids = registry.register_compiler_run(report, timestamp="2026-08-14T00:00:00+00:00")
    for candidate_id in candidate_ids:
        candidate = registry.get_candidate(candidate_id)
        resolutions = {identifier: "reviewed" for identifier in candidate.get("conflict_ids", [])}
        registry.submit_review(
            candidate_id,
            "reviewer-a",
            "DOMAIN_REVIEWER",
            "APPROVE",
            "domain approval",
            resolutions=resolutions,
            timestamp="2026-08-14T00:01:00+00:00",
        )
        if candidate["mechanism"]["risk_class"] in {"HIGH", "CRITICAL"}:
            registry.submit_review(
                candidate_id,
                "reviewer-b",
                "SAFETY_REVIEWER",
                "APPROVE",
                "safety approval",
                resolutions=resolutions,
                timestamp="2026-08-14T00:02:00+00:00",
            )
        registry.promote(candidate_id, "release-manager", timestamp="2026-08-14T00:03:00+00:00")
    return registry, report


class RegistryRuntimeTests(unittest.TestCase):
    def test_high_risk_requires_two_reviews_and_resolutions(self):
        report = compile_institution(EXAMPLE)
        with tempfile.TemporaryDirectory() as directory:
            registry = ReviewRegistry(Path(directory) / "registry.sqlite3")
            ids = registry.register_compiler_run(report, timestamp="2026-08-14T00:00:00+00:00")
            high_id = next(
                candidate_id for candidate_id in ids
                if registry.get_candidate(candidate_id)["mechanism"]["risk_class"] == "HIGH"
            )
            candidate = registry.get_candidate(high_id)
            with self.assertRaisesRegex(RegistryError, "explicit resolutions"):
                registry.submit_review(
                    high_id, "reviewer-a", "DOMAIN_REVIEWER", "APPROVE", "reviewed"
                )
            resolutions = {identifier: "normative value retained" for identifier in candidate["conflict_ids"]}
            first = registry.submit_review(
                high_id,
                "reviewer-a",
                "DOMAIN_REVIEWER",
                "APPROVE",
                "reviewed",
                resolutions=resolutions,
                timestamp="2026-08-14T00:01:00+00:00",
            )
            self.assertEqual(first["status"], "UNDER_REVIEW")
            with self.assertRaises(sqlite3.DatabaseError):
                with closing(sqlite3.connect(registry.path)) as connection:
                    connection.execute("UPDATE reviews SET rationale = 'tampered'")
            with self.assertRaisesRegex(RegistryError, "not ready"):
                registry.promote(high_id, "release-manager")
            second = registry.submit_review(
                high_id,
                "reviewer-b",
                "SAFETY_REVIEWER",
                "APPROVE",
                "independent review",
                resolutions=resolutions,
                timestamp="2026-08-14T00:02:00+00:00",
            )
            self.assertEqual(second["status"], "READY_TO_PROMOTE")
            mechanism = registry.promote(
                high_id, "release-manager", timestamp="2026-08-14T00:03:00+00:00"
            )
            self.assertTrue(mechanism["approved"])
            self.assertFalse(mechanism["binding_authority"])
            self.assertTrue(registry.verify_audit_chain())

    def test_new_version_can_be_rolled_back_without_deleting_history(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            registry, _ = promoted_registry(root)
            raw = json.loads(EXAMPLE.read_text(encoding="utf-8"))
            raw["compiler_run_id"] = "synthetic-hospital-compiler-run-002"
            raw["institution_version"] = "0.2.0"
            input_path = root / "compiler-v2.json"
            input_path.write_text(json.dumps(raw), encoding="utf-8")
            report = compile_institution(input_path)
            ids = registry.register_compiler_run(report, timestamp="2026-08-14T00:10:00+00:00")
            candidate_id = next(
                identifier for identifier in ids
                if registry.get_candidate(identifier)["mechanism"]["mechanism_id"] == "medication-release"
            )
            candidate = registry.get_candidate(candidate_id)
            resolutions = {identifier: "reviewed v2" for identifier in candidate["conflict_ids"]}
            registry.submit_review(
                candidate_id, "v2-domain", "DOMAIN_REVIEWER", "APPROVE", "v2 domain",
                resolutions=resolutions, timestamp="2026-08-14T00:11:00+00:00"
            )
            registry.submit_review(
                candidate_id, "v2-safety", "SAFETY_REVIEWER", "APPROVE", "v2 safety",
                resolutions=resolutions, timestamp="2026-08-14T00:12:00+00:00"
            )
            registry.promote(candidate_id, "release-manager", timestamp="2026-08-14T00:13:00+00:00")
            self.assertEqual(registry.get_mechanism("medication-release")["version"], "0.2.0")
            restored = registry.rollback(
                "medication-release", "0.1.0", "release-manager", "regression detected",
                timestamp="2026-08-14T00:14:00+00:00"
            )
            self.assertEqual(restored["version"], "0.1.0")
            self.assertEqual(registry.get_mechanism("medication-release")["version"], "0.1.0")
            self.assertEqual(len([
                row for row in registry.list_mechanisms()
                if row["mechanism_id"] == "medication-release"
            ]), 2)
            self.assertTrue(registry.verify_audit_chain())

    def test_runtime_actionnet_and_qualification(self):
        with tempfile.TemporaryDirectory() as directory:
            registry, _ = promoted_registry(Path(directory))
            mechanism = registry.get_mechanism("medication-release")
            runtime = InstitutionalRuntime()
            state = {"facts": expected_facts(mechanism)}
            self.assertEqual(runtime.evaluate(mechanism, state).decision.value, "ALLOW")
            bad = deepcopy(state)
            path = next(iter(sorted(bad["facts"])))
            bad["facts"][path] = "wrong"
            self.assertEqual(runtime.evaluate(mechanism, bad).decision.value, "DENY")
            bundle = generate_actionnet(mechanism, generator_seed=11)
            qualification = qualify_actionnet(mechanism, bundle)
            self.assertTrue(qualification["passed"], qualification["diagnostics"])
            self.assertEqual(bundle["manifest"]["case_count"], 18)
            self.assertNotIn("labels", json.dumps(bundle["public"]))


class OrchestrationShadowTests(unittest.TestCase):
    def test_orchestration_shadow_and_gap_discovery(self):
        with tempfile.TemporaryDirectory() as directory:
            registry, _ = promoted_registry(Path(directory))
            mechanism = registry.get_mechanism("medication-release")
            bundle = generate_actionnet(mechanism)
            qualification = qualify_actionnet(mechanism, bundle)
            orchestrator = TrainingOrchestrator(Path(directory) / "campaigns")
            manifest = orchestrator.prepare_campaign(
                "campaign", bundle, qualification, [1, 2], condition="REFERENCE_ORACLE_PLUMBING"
            )
            self.assertTrue(manifest["labels_separated"])
            evaluations = orchestrator.reference_oracle_diagnostic(bundle, [1, 2])
            summary = orchestrator.summarize_gates("campaign", evaluations, [1, 2])
            self.assertTrue(summary["passed"])
            self.assertTrue(all(not row["learning_claim"] for row in evaluations))

            records = [
                {
                    "shadow_id": f"s-{index}",
                    "mechanism_id": "medication-release",
                    "context": {"case": index},
                    "human_decision": "ALLOW",
                    "system_decision": "ALLOW",
                    "cerebrum_decision": "DENY",
                    "runtime_decision": "DENY",
                    "runtime_failed_conditions": ["MISMATCH:medication_release.authorized_role"],
                }
                for index in range(3)
            ]
            shadow = run_shadow_comparison(records)
            gaps = discover_gaps(shadow, minimum_repetitions=2)
            self.assertEqual(shadow["summary"]["disagreement_count"], 3)
            self.assertEqual(gaps["proposal_count"], 1)
            self.assertEqual(gaps["proposals"][0]["gap_type"], "MISSING_AUTHORITY_RELATIONSHIP")


class APITests(unittest.TestCase):
    def test_api_authentication_and_role_enforcement(self):
        with tempfile.TemporaryDirectory() as directory:
            service = PlatformService(directory)
            server = EDONHTTPServer(
                ("127.0.0.1", 0),
                service,
                {"viewer-token-000000": "VIEWER", "admin-token-0000000": "ADMIN"},
            )
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            base = f"http://127.0.0.1:{server.server_address[1]}"
            try:
                with urllib.request.urlopen(base + "/health") as response:
                    self.assertEqual(response.status, 200)
                with self.assertRaises(urllib.error.HTTPError) as unauthorized:
                    urllib.request.urlopen(base + "/api/status")
                self.assertEqual(unauthorized.exception.code, 401)
                request = urllib.request.Request(
                    base + "/api/status",
                    headers={"Authorization": "Bearer viewer-token-000000"},
                )
                with urllib.request.urlopen(request) as response:
                    self.assertEqual(response.status, 200)
                forbidden = urllib.request.Request(
                    base + "/api/compile",
                    data=EXAMPLE.read_bytes(),
                    method="POST",
                    headers={
                        "Authorization": "Bearer viewer-token-000000",
                        "X-EDON-Role": "ADMIN",
                        "Content-Type": "application/json",
                    },
                )
                with self.assertRaises(urllib.error.HTTPError) as denied:
                    urllib.request.urlopen(forbidden)
                self.assertEqual(denied.exception.code, 403)
            finally:
                server.shutdown()
                server.server_close()
                thread.join(timeout=5)


if __name__ == "__main__":
    unittest.main()