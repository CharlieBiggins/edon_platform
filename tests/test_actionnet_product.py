import json
import os
import sqlite3
import subprocess
import sys
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from contextlib import closing
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from edon.actionnet.product import (
    ActionNetPlatformStore,
    GovernedAbstractionValidator,
    GovernedIntakeError,
)
from edon.api.server import EDONHTTPServer, PlatformService
from edon.evaluation import run_actionnet_platform001, run_actionnet_platform002


class ActionNetProductTests(unittest.TestCase):
    def test_complete_product_workflow_gate(self):
        result = run_actionnet_platform001()
        self.assertEqual(result["status"], "PASS", result["gates"])
        self.assertEqual(result["checks_passed"], 18)
        self.assertEqual(result["check_count"], 18)
        self.assertFalse(result["production_ready"])

    def test_active_experience_upgrade_gate(self):
        result = run_actionnet_platform002()
        self.assertEqual(result["status"], "PASS", result["gates"])
        self.assertEqual(result["checks_passed"], 26)
        self.assertEqual(result["check_count"], 26)
        self.assertFalse(result["production_ready"])

    def test_governed_abstraction_rejects_raw_sensitive_fields(self):
        validator = GovernedAbstractionValidator()
        with self.assertRaises(GovernedIntakeError):
            validator.normalize({
                "intake_id": "unsafe", "patient_name": "must-not-enter-platform",
                "institution_ir_ref": {"institution_id": "x", "version": "1"},
                "source_fingerprint": "sha256:x",
                "local_processor": {"processor_id": "edge", "version": "1"},
                "rights_basis": "INTERNAL_AUTHORIZATION", "data_categories": [],
                "redaction_summary": {},
                "attestation": {
                    "direct_identifiers_removed": True, "secrets_removed": True,
                    "minimum_necessary": True, "raw_payload_retained_locally": True,
                    "authorized_for_abstraction": True,
                },
                "mechanism_refs": [{"mechanism_id": "m", "version": "1"}],
                "trajectory": {}, "causal_trace": {}, "provenance": {},
            })

    def test_platform002_api_registers_ir_and_separates_intake_role(self):
        with tempfile.TemporaryDirectory() as directory:
            server = EDONHTTPServer(
                ("127.0.0.1", 0), PlatformService(directory),
                {
                    "author-token-platform002-000000": {
                        "role": "ACTIONNET_AUTHOR", "tenant_id": "tenant"
                    },
                    "intake-token-platform002-000000": {
                        "role": "ACTIONNET_INTAKE_OPERATOR", "tenant_id": "tenant"
                    },
                },
            )
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            base = f"http://127.0.0.1:{server.server_address[1]}"

            def post(path, token, body):
                request = urllib.request.Request(
                    base + path, data=json.dumps(body).encode("utf-8"), method="POST",
                    headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
                )
                with urllib.request.urlopen(request) as response:
                    return json.loads(response.read().decode("utf-8"))

            try:
                record = post(
                    "/api/actionnet-platform/institutional-ir",
                    "author-token-platform002-000000",
                    {
                        "tenant_id": "tenant", "institution_id": "institution",
                        "version": "1.0.0", "institutional_ir": {
                            "institution_id": "institution", "version": "1.0.0",
                            "institution_type": "TEST", "objects": [
                                {"object_id": "institution", "object_type": "INSTITUTION", "attributes": {}}
                            ],
                        },
                    },
                )
                self.assertEqual(record["institutional_ir"]["canonical_tuple"], "I=(X,E,R,A,P,W,T,C,Sigma)")
                with self.assertRaises(urllib.error.HTTPError) as denied:
                    post(
                        "/api/actionnet-platform/intake",
                        "author-token-platform002-000000",
                        {"tenant_id": "tenant"},
                    )
                self.assertEqual(denied.exception.code, 403)
            finally:
                server.shutdown()
                server.server_close()
                thread.join(timeout=5)

    def test_product_records_are_immutable(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "platform.sqlite3"
            store = ActionNetPlatformStore(path)
            store.register_mechanism(
                "tenant", "mechanism", "1.0.0", "Mechanism",
                "A sufficiently detailed mechanism description.",
                {
                    "preconditions": [], "state_transitions": [], "dependencies": [],
                    "interventions": [], "failure_modes": [], "expected_outcomes": [],
                },
                created_by="author",
            )
            with self.assertRaises(sqlite3.DatabaseError):
                with closing(sqlite3.connect(path)) as connection:
                    connection.execute(
                        "UPDATE actionnet_mechanisms SET title = 'Changed'"
                    )

    def test_api_enforces_protected_custody_and_review_roles(self):
        with tempfile.TemporaryDirectory() as directory:
            server = EDONHTTPServer(
                ("127.0.0.1", 0), PlatformService(directory),
                {
                    "author-token-0000000": {
                        "role": "ACTIONNET_AUTHOR", "tenant_id": "tenant"
                    },
                    "custodian-token-0000": "ACTIONNET_CUSTODIAN",
                    "domain-token-0000000": "ACTIONNET_DOMAIN_REVIEWER",
                },
            )
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            base = f"http://127.0.0.1:{server.server_address[1]}"

            def post(path, token, body):
                request = urllib.request.Request(
                    base + path, data=json.dumps(body).encode("utf-8"), method="POST",
                    headers={
                        "Authorization": f"Bearer {token}",
                        "Content-Type": "application/json",
                    },
                )
                with urllib.request.urlopen(request) as response:
                    return json.loads(response.read().decode("utf-8"))

            mechanism_body = {
                "tenant_id": "tenant", "mechanism_id": "capacity", "version": "1.0.0",
                "title": "Capacity", "description": "Capacity declines under a registered event.",
                "specification": {
                    "preconditions": [], "state_transitions": [], "dependencies": [],
                    "interventions": [], "failure_modes": [], "expected_outcomes": [],
                },
                "evidence_grade": "SYNTHETIC_VERIFIED",
            }
            experience_body = {
                "tenant_id": "tenant", "experience_id": "experience",
                "source_type": "SIMULATOR", "institution_type": "logistics",
                "mechanism_refs": [{"mechanism_id": "capacity", "version": "1.0.0"}],
                "trajectory": {"state": "changed"},
                "causal_trace": {"path": ["capacity", "outcome"]},
                "evidence_grade": "SYNTHETIC_VERIFIED", "provenance": {},
            }
            try:
                post(
                    "/api/actionnet-platform/mechanisms",
                    "author-token-0000000", mechanism_body,
                )
                normal = post(
                    "/api/actionnet-platform/experiences",
                    "author-token-0000000", experience_body,
                )
                self.assertFalse(normal["protected"])
                with self.assertRaises(urllib.error.HTTPError) as denied:
                    post(
                        "/api/actionnet-platform/experiences",
                        "author-token-0000000",
                        {**experience_body, "experience_id": "protected", "protected": True},
                    )
                self.assertEqual(denied.exception.code, 400)
                protected = post(
                    "/api/actionnet-platform/experiences",
                    "custodian-token-0000",
                    {**experience_body, "experience_id": "protected", "protected": True},
                )
                self.assertTrue(protected["protected"])
                with self.assertRaises(urllib.error.HTTPError) as wrong_role:
                    post(
                        "/api/actionnet-platform/reviews",
                        "domain-token-0000000",
                        {
                            "tenant_id": "tenant", "review_id": "review",
                            "experience_id": "experience", "dimension": "SAFETY",
                            "decision": "APPROVE",
                            "rationale": "Attempted approval under the wrong reviewer role.",
                        },
                    )
                self.assertEqual(wrong_role.exception.code, 400)
                with self.assertRaises(urllib.error.HTTPError) as wrong_tenant:
                    post(
                        "/api/actionnet-platform/mechanisms",
                        "author-token-0000000",
                        {**mechanism_body, "tenant_id": "different-tenant", "version": "2.0.0"},
                    )
                self.assertEqual(wrong_tenant.exception.code, 400)
            finally:
                server.shutdown()
                server.server_close()
                thread.join(timeout=5)

    def test_backup_verification_and_internal_readiness(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            state = root / "state"
            state.mkdir()
            store = ActionNetPlatformStore(state / "actionnet-platform.sqlite3")
            store.register_mechanism(
                "tenant", "mechanism", "1.0.0", "Mechanism",
                "A sufficiently detailed mechanism description.",
                {
                    "preconditions": [], "state_transitions": [], "dependencies": [],
                    "interventions": [], "failure_modes": [], "expected_outcomes": [],
                },
                created_by="author",
            )
            backups = root / "backups"
            backup = subprocess.run(
                [
                    sys.executable, "scripts/actionnet/backup_platform.py",
                    "--state-dir", str(state), "--output-dir", str(backups),
                ],
                cwd=ROOT, capture_output=True, text=True, check=False,
            )
            self.assertEqual(backup.returncode, 0, backup.stderr)
            manifest = next(backups.glob("*.manifest.json"))
            verification = subprocess.run(
                [sys.executable, "scripts/actionnet/verify_backup.py", str(manifest)],
                cwd=ROOT, capture_output=True, text=True, check=False,
            )
            self.assertEqual(verification.returncode, 0, verification.stdout)
            self.assertEqual(json.loads(verification.stdout)["status"], "PASS")
            environment = dict(os.environ)
            environment["EDON_API_KEYS"] = json.dumps({
                "x" * 40: {"role": "ACTIONNET_AUTHOR", "tenant_id": "tenant"}
            })
            readiness = subprocess.run(
                [
                    sys.executable, "scripts/actionnet/readiness.py",
                    "--state-dir", str(state),
                ],
                cwd=ROOT, env=environment, capture_output=True, text=True, check=False,
            )
            self.assertEqual(readiness.returncode, 0, readiness.stdout)
            report = json.loads(readiness.stdout)
            self.assertEqual(report["status"], "INTERNAL_MVP_READY")
            self.assertFalse(report["production_ready"])


if __name__ == "__main__":
    unittest.main()