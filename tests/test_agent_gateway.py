import json
import sqlite3
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

from edon.api.server import EDONHTTPServer, PlatformService
from edon.gateway import AgentGateway, AgentGatewayError, AgentGatewayStore


def connector(connector_id="mcp-main", tenant_id="tenant-a", protocol="MCP"):
    versions = {
        "MCP": "2026-07-28", "A2A": "1.0", "REST": "1.0",
        "WEBHOOK": "1.0", "FHIR_R4_SMART": "R4",
    }
    operations = {
        "MCP": ["tools/call"], "A2A": ["SendMessage"],
        "REST": ["OBSERVATION_RECEIVED"], "WEBHOOK": ["OBSERVATION_RECEIVED"],
        "FHIR_R4_SMART": ["READ", "SEARCH", "EVENT"],
    }
    targets = {
        "MCP": ["edon.submit_shadow_proposal"],
        "A2A": ["edon-shadow-supervisor"],
        "REST": ["operations.observations"],
        "WEBHOOK": ["operations.observations"],
        "FHIR_R4_SMART": ["Patient", "Observation"],
    }
    return {
        "connector_id": connector_id,
        "tenant_id": tenant_id,
        "vendor_id": "test-vendor",
        "protocol": protocol,
        "protocol_version": versions[protocol],
        "endpoint": "https://agents.example.test/gateway",
        "auth_method": "OAUTH2_CLIENT_CREDENTIALS",
        "credential_secret_ref": f"secret://gateway/{connector_id}",
        "allowed_operations": operations[protocol],
        "allowed_targets": targets[protocol],
        "mode": "READ_ONLY" if protocol == "FHIR_R4_SMART" else "SHADOW",
        "sensitivity_ceiling": "CONFIDENTIAL",
        "data_residency": "US",
        "actor_id": "gateway-admin",
        "binding_authority": False,
    }


def message(connector_id="mcp-main", protocol="MCP", message_id="message-001", key="request-001"):
    bodies = {
        "MCP": {
            "jsonrpc": "2.0", "id": "call-001", "method": "tools/call",
            "params": {
                "name": "edon.submit_shadow_proposal",
                "arguments": {"observation_id": "obs-001"},
            },
        },
        "A2A": {
            "jsonrpc": "2.0", "id": "a2a-001", "operation": "SendMessage",
            "skill_id": "edon-shadow-supervisor",
            "params": {"message": {"text": "Review current state."}},
        },
        "REST": {
            "operation": "OBSERVATION_RECEIVED", "target": "operations.observations",
            "payload": {"observation_id": "obs-001"},
        },
        "WEBHOOK": {
            "operation": "OBSERVATION_RECEIVED", "target": "operations.observations",
            "payload": {"observation_id": "obs-001"},
        },
        "FHIR_R4_SMART": {
            "operation": "READ", "resource_type": "Patient",
            "payload": {"id": "patient-redacted"},
        },
    }
    versions = {
        "MCP": "2026-07-28", "A2A": "1.0", "REST": "1.0",
        "WEBHOOK": "1.0", "FHIR_R4_SMART": "R4",
    }
    return {
        "tenant_id": "tenant-a", "connector_id": connector_id,
        "protocol": protocol, "protocol_version": versions[protocol],
        "message_id": message_id, "idempotency_key": key,
        "occurred_at": "2026-08-29T12:00:00Z", "sensitivity": "CONFIDENTIAL",
        "trace_context": {
            "traceparent": "00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01"
        },
        "body": bodies[protocol], "actor_id": "gateway-ingress",
    }


class AgentGatewayTests(unittest.TestCase):
    def enable(self, gateway, connector_id):
        return gateway.set_connector_status({
            "connector_id": connector_id, "tenant_id": "tenant-a",
            "status": "ENABLED", "security_review_ref": f"review-{connector_id}",
            "actor_id": "gateway-admin",
        })

    def test_custody_replay_and_authority_boundary(self):
        with tempfile.TemporaryDirectory() as directory:
            store = AgentGatewayStore(Path(directory) / "gateway.sqlite3")
            gateway = AgentGateway(store)
            self.assertEqual(gateway.register_connector(connector())["status"], "DISABLED")
            with self.assertRaisesRegex(AgentGatewayError, "not enabled"):
                gateway.ingest(message())
            self.enable(gateway, "mcp-main")
            result = gateway.ingest(message())
            self.assertEqual(result["receipt"]["status"], "ACCEPTED_SHADOW_ONLY")
            self.assertFalse(result["receipt"]["executed"])
            self.assertNotIn("obs-001", json.dumps(result["telemetry"]))
            self.assertEqual(
                result["receipt"]["envelope_sha256"],
                gateway.ingest(message())["receipt"]["envelope_sha256"],
            )
            changed = message(message_id="changed")
            changed["body"]["params"]["arguments"]["observation_id"] = "different"
            with self.assertRaisesRegex(AgentGatewayError, "idempotency key"):
                gateway.ingest(changed)
            unsafe = message(message_id="unsafe", key="unsafe")
            unsafe["body"]["params"]["arguments"]["execution_token"] = "forged"
            with self.assertRaisesRegex(AgentGatewayError, "authority fields"):
                gateway.ingest(unsafe)
            self.assertTrue(store.verify_audit_chain())
            with self.assertRaises(sqlite3.DatabaseError):
                with closing(sqlite3.connect(store.path)) as connection:
                    connection.execute("DELETE FROM gateway_messages")

    def test_all_protocols_tenant_isolation_and_fhir_read_only(self):
        with tempfile.TemporaryDirectory() as directory:
            gateway = AgentGateway(AgentGatewayStore(Path(directory) / "gateway.sqlite3"))
            for protocol, connector_id in (
                ("A2A", "a2a-main"), ("REST", "rest-main"),
                ("WEBHOOK", "webhook-main"), ("FHIR_R4_SMART", "fhir-main"),
            ):
                gateway.register_connector(connector(connector_id, protocol=protocol))
                self.enable(gateway, connector_id)
                result = gateway.ingest(message(
                    connector_id, protocol, f"message-{connector_id}", f"key-{connector_id}"
                ))
                self.assertFalse(result["binding_authority"])
            wrong = message("a2a-main", "A2A", "wrong", "wrong")
            wrong["tenant_id"] = "tenant-b"
            with self.assertRaisesRegex(AgentGatewayError, "connector.*tenant"):
                gateway.ingest(wrong)
            write = message("fhir-main", "FHIR_R4_SMART", "fhir-write", "fhir-write")
            write["body"]["operation"] = "UPDATE"
            with self.assertRaisesRegex(AgentGatewayError, "writes are prohibited"):
                gateway.ingest(write)
            audit = gateway.audit({"tenant_id": "tenant-a"})
            self.assertTrue(audit["chain_valid"])
            self.assertTrue(all(row["payload"]["tenant_id"] == "tenant-a" for row in audit["items"]))
            self.assertTrue(all(not row["production_validated"] for row in gateway.vendors()["items"]))


class AgentGatewayAPITests(unittest.TestCase):
    def test_api_role_and_tenant_boundaries(self):
        with tempfile.TemporaryDirectory() as directory:
            server = EDONHTTPServer(
                ("127.0.0.1", 0), PlatformService(directory),
                {
                    "gateway-admin-token-0001": {"role": "GATEWAY_ADMIN", "tenant_id": "tenant-a"},
                    "gateway-ingress-token-01": {"role": "GATEWAY_INGRESS", "tenant_id": "tenant-a"},
                },
            )
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            base = f"http://127.0.0.1:{server.server_address[1]}"

            def post(path, token, body):
                request = urllib.request.Request(
                    base + path, data=json.dumps(body).encode(), method="POST",
                    headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
                )
                with urllib.request.urlopen(request) as response:
                    return json.loads(response.read())

            try:
                profile = connector()
                profile.pop("actor_id")
                self.assertEqual(
                    post("/api/gateway/connectors", "gateway-admin-token-0001", profile)["tenant_id"],
                    "tenant-a",
                )
                post("/api/gateway/connectors/status", "gateway-admin-token-0001", {
                    "connector_id": "mcp-main", "status": "ENABLED",
                    "security_review_ref": "security-review-001",
                })
                inbound = message()
                inbound.pop("actor_id")
                self.assertEqual(
                    post("/api/gateway/messages", "gateway-ingress-token-01", inbound)["receipt"]["status"],
                    "ACCEPTED_SHADOW_ONLY",
                )
                with self.assertRaises(urllib.error.HTTPError) as denied:
                    post("/api/gateway/connectors", "gateway-ingress-token-01", profile)
                self.assertEqual(denied.exception.code, 403)
                denied.exception.close()
                other = connector(tenant_id="tenant-b")
                other.pop("actor_id")
                with self.assertRaises(urllib.error.HTTPError) as denied_tenant:
                    post("/api/gateway/connectors", "gateway-admin-token-0001", other)
                self.assertEqual(denied_tenant.exception.code, 400)
                denied_tenant.exception.close()
            finally:
                server.shutdown()
                server.server_close()
                thread.join(timeout=5)


if __name__ == "__main__":
    unittest.main()