"""EDON-AGENT-GATEWAY-001 internal protocol and authority-boundary evaluation."""

from __future__ import annotations

import json
import sqlite3
import tempfile
from contextlib import closing
from pathlib import Path

from edon.gateway import AgentGateway, AgentGatewayError, AgentGatewayStore


def _connector(connector_id: str, protocol: str, operations: list[str], targets: list[str]) -> dict:
    versions = {"MCP": "2026-07-28", "FHIR_R4_SMART": "R4"}
    return {
        "connector_id": connector_id,
        "tenant_id": "evaluation-tenant",
        "vendor_id": "evaluation-vendor",
        "protocol": protocol,
        "protocol_version": versions[protocol],
        "endpoint": "https://gateway.example.test/agent",
        "auth_method": "OAUTH2_CLIENT_CREDENTIALS",
        "credential_secret_ref": f"secret://evaluation/{connector_id}",
        "allowed_operations": operations,
        "allowed_targets": targets,
        "mode": "READ_ONLY" if protocol == "FHIR_R4_SMART" else "SHADOW",
        "sensitivity_ceiling": "CONFIDENTIAL",
        "data_residency": "US",
        "actor_id": "evaluation-admin",
        "binding_authority": False,
    }


def _mcp_message(message_id: str = "mcp-message", idempotency_key: str = "mcp-request") -> dict:
    return {
        "tenant_id": "evaluation-tenant",
        "connector_id": "mcp-evaluation",
        "protocol": "MCP",
        "protocol_version": "2026-07-28",
        "message_id": message_id,
        "idempotency_key": idempotency_key,
        "occurred_at": "2026-08-29T12:00:00Z",
        "sensitivity": "CONFIDENTIAL",
        "body": {
            "jsonrpc": "2.0",
            "id": "rpc-1",
            "method": "tools/call",
            "params": {
                "name": "edon.submit_shadow_proposal",
                "arguments": {"observation_id": "observation-redacted"},
            },
        },
        "actor_id": "evaluation-ingress",
    }


def run_agent_gateway001() -> dict:
    with tempfile.TemporaryDirectory() as directory:
        store = AgentGatewayStore(Path(directory) / "gateway.sqlite3")
        gateway = AgentGateway(store)
        registered = gateway.register_connector(
            _connector(
                "mcp-evaluation", "MCP", ["tools/call"],
                ["edon.submit_shadow_proposal"],
            )
        )
        disabled_rejected = False
        try:
            gateway.ingest(_mcp_message())
        except AgentGatewayError:
            disabled_rejected = True
        enabled = gateway.set_connector_status(
            {
                "connector_id": "mcp-evaluation",
                "tenant_id": "evaluation-tenant",
                "status": "ENABLED",
                "security_review_ref": "security-review-evaluation",
                "actor_id": "evaluation-admin",
            }
        )
        accepted = gateway.ingest(_mcp_message())
        repeated = gateway.ingest(_mcp_message())

        replay_rebinding_rejected = False
        changed = _mcp_message("mcp-message-changed")
        changed["body"]["params"]["arguments"]["observation_id"] = "changed"
        try:
            gateway.ingest(changed)
        except AgentGatewayError:
            replay_rebinding_rejected = True

        authority_smuggling_rejected = False
        unsafe = _mcp_message("mcp-unsafe", "mcp-unsafe")
        unsafe["body"]["params"]["arguments"]["kernel_token"] = "forged"
        try:
            gateway.ingest(unsafe)
        except AgentGatewayError:
            authority_smuggling_rejected = True

        tenant_isolation = False
        wrong_tenant = _mcp_message("wrong-tenant", "wrong-tenant")
        wrong_tenant["tenant_id"] = "other-tenant"
        try:
            gateway.ingest(wrong_tenant)
        except AgentGatewayError:
            tenant_isolation = True

        gateway.register_connector(
            _connector(
                "fhir-evaluation", "FHIR_R4_SMART", ["READ", "SEARCH", "EVENT"],
                ["Patient", "Observation"],
            )
        )
        gateway.set_connector_status(
            {
                "connector_id": "fhir-evaluation",
                "tenant_id": "evaluation-tenant",
                "status": "ENABLED",
                "security_review_ref": "security-review-fhir",
                "actor_id": "evaluation-admin",
            }
        )
        fhir_write_rejected = False
        try:
            gateway.ingest(
                {
                    "tenant_id": "evaluation-tenant",
                    "connector_id": "fhir-evaluation",
                    "protocol": "FHIR_R4_SMART",
                    "protocol_version": "R4",
                    "message_id": "fhir-write",
                    "idempotency_key": "fhir-write",
                    "occurred_at": "2026-08-29T12:01:00Z",
                    "sensitivity": "CONFIDENTIAL",
                    "body": {
                        "operation": "UPDATE",
                        "resource_type": "Patient",
                        "payload": {"id": "redacted"},
                    },
                    "actor_id": "evaluation-ingress",
                }
            )
        except AgentGatewayError:
            fhir_write_rejected = True

        immutable_messages = False
        try:
            with closing(sqlite3.connect(store.path)) as connection:
                connection.execute("DELETE FROM gateway_messages")
        except sqlite3.DatabaseError:
            immutable_messages = True

        capabilities = gateway.capabilities()
        vendors = gateway.vendors()["items"]
        telemetry_text = json.dumps(accepted["telemetry"], sort_keys=True)
        audit = gateway.audit({"tenant_id": "evaluation-tenant"})
        gates = {
            "connector_registered_disabled": registered["status"] == "DISABLED",
            "disabled_connector_rejected": disabled_rejected,
            "enablement_requires_recorded_review": (
                enabled["status"] == "ENABLED"
                and enabled["security_review_ref"] == "security-review-evaluation"
            ),
            "mcp_version_pinned": capabilities["protocol_versions"]["MCP"] == "2026-07-28",
            "a2a_version_pinned": capabilities["protocol_versions"]["A2A"] == "1.0",
            "ingress_is_shadow_only": accepted["receipt"]["status"] == "ACCEPTED_SHADOW_ONLY",
            "ingress_is_non_binding": accepted["receipt"]["binding_authority"] is False,
            "ingress_is_not_execution": accepted["receipt"]["executed"] is False,
            "idempotent_replay_is_stable": (
                accepted["receipt"]["envelope_sha256"]
                == repeated["receipt"]["envelope_sha256"]
            ),
            "idempotency_rebinding_rejected": replay_rebinding_rejected,
            "authority_smuggling_rejected": authority_smuggling_rejected,
            "tenant_isolation": tenant_isolation,
            "fhir_writes_rejected": fhir_write_rejected,
            "message_records_immutable": immutable_messages,
            "audit_chain_valid": audit["chain_valid"],
            "telemetry_excludes_message_content": "observation-redacted" not in telemetry_text,
            "vendor_profiles_are_not_certification_claims": (
                len(vendors) == 11 and all(not item["production_validated"] for item in vendors)
            ),
            "delivery_worker_disabled": capabilities["delivery_worker_implemented"] is False,
            "gateway_has_no_direct_execution": capabilities["direct_execution"] is False,
        }
        return {
            "schema_version": "edon-agent-gateway-001-evaluation.v1",
            "evaluation_id": "EDON-AGENT-GATEWAY-001",
            "status": "PASS" if all(gates.values()) else "FAIL",
            "gates": gates,
            "checks_passed": sum(gates.values()),
            "check_count": len(gates),
            "production_ready": False,
            "binding_authority": False,
            "claim_scope": "Internal protocol normalization, custody, tenancy, and authority-boundary evidence only",
        }