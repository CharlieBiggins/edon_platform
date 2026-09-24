"""Non-binding protocol service for the EDON Agent Gateway."""

from __future__ import annotations

from typing import Any

from .models import (
    CONNECTOR_STATUSES,
    PROTOCOL_VERSIONS,
    AgentGatewayError,
    ConnectorProfile,
    GatewayEnvelope,
    identifier,
)
from .protocols import normalize_protocol_message
from .store import AgentGatewayStore
from .telemetry import otlp_span
from .vendors import vendor_profiles


class AgentGateway:
    """Registers connectors and records normalized shadow-only envelopes."""

    def __init__(self, store: AgentGatewayStore):
        self.store = store

    def register_connector(self, body: dict[str, Any]) -> dict[str, Any]:
        profile = ConnectorProfile.from_dict(body).as_dict()
        actor_id = identifier(body.get("actor_id"), "actor_id")
        return self.store.register_connector(profile, actor_id=actor_id)

    def set_connector_status(self, body: dict[str, Any]) -> dict[str, Any]:
        tenant_id = identifier(body.get("tenant_id"), "tenant_id")
        connector_id = identifier(body.get("connector_id"), "connector_id")
        actor_id = identifier(body.get("actor_id"), "actor_id")
        status = str(body.get("status", "")).upper()
        if status not in CONNECTOR_STATUSES:
            raise AgentGatewayError("unsupported connector status")
        profile = self.store.connector(tenant_id, connector_id)
        review = str(body.get("security_review_ref", "")).strip() or None
        if status == "ENABLED":
            if not review:
                raise AgentGatewayError("connector enablement requires security_review_ref")
            if not profile.get("credential_secret_ref"):
                raise AgentGatewayError("connector enablement requires credential_secret_ref")
            if profile.get("auth_method") == "NONE_DEV_ONLY":
                raise AgentGatewayError("development-only authentication cannot be enabled")
        return self.store.set_connector_status(
            tenant_id,
            connector_id,
            status,
            security_review_ref=review,
            actor_id=actor_id,
        )

    def _normalize(
        self,
        request: dict[str, Any],
        *,
        direction: str,
    ) -> tuple[dict[str, Any], dict[str, Any], str]:
        if not isinstance(request, dict):
            raise AgentGatewayError("gateway request must be an object")
        tenant_id = identifier(request.get("tenant_id"), "tenant_id")
        connector_id = identifier(request.get("connector_id"), "connector_id")
        actor_id = identifier(request.get("actor_id"), "actor_id")
        profile = self.store.connector(tenant_id, connector_id)
        if profile["status"] != "ENABLED":
            raise AgentGatewayError("connector is not enabled")
        if str(request.get("protocol", "")).upper() != profile["protocol"]:
            raise AgentGatewayError("message protocol does not match connector")
        if str(request.get("protocol_version", "")) != profile["protocol_version"]:
            raise AgentGatewayError("message protocol version does not match connector")
        normalized = normalize_protocol_message(profile, request)
        envelope = GatewayEnvelope.create(
            profile=profile,
            direction=direction,
            message_id=normalized["message_id"],
            message_type=normalized["message_type"],
            occurred_at=normalized["occurred_at"],
            idempotency_key=normalized["idempotency_key"],
            sensitivity=normalized["sensitivity"],
            trace_context=normalized["trace_context"],
            payload=normalized["payload"],
        ).as_dict()
        return profile, envelope, actor_id

    def ingest(self, request: dict[str, Any]) -> dict[str, Any]:
        profile, envelope, actor_id = self._normalize(request, direction="INGRESS")
        receipt = self.store.record_envelope(
            envelope,
            receipt_status="ACCEPTED_SHADOW_ONLY",
            actor_id=actor_id,
        )
        return {
            "receipt": receipt,
            "envelope": envelope,
            "telemetry": otlp_span(
                envelope,
                endpoint=profile["endpoint"],
                status=receipt["status"],
            ),
            "binding_authority": False,
        }

    def stage_egress(self, request: dict[str, Any]) -> dict[str, Any]:
        profile, envelope, actor_id = self._normalize(request, direction="EGRESS")
        receipt = self.store.record_envelope(
            envelope,
            receipt_status="STAGED_NOT_DELIVERED",
            actor_id=actor_id,
        )
        return {
            "receipt": receipt,
            "envelope": envelope,
            "telemetry": otlp_span(
                envelope,
                endpoint=profile["endpoint"],
                status=receipt["status"],
            ),
            "binding_authority": False,
        }

    def connectors(self, body: dict[str, Any]) -> dict[str, Any]:
        tenant_id = identifier(body.get("tenant_id"), "tenant_id")
        return {
            "items": self.store.list_connectors(tenant_id),
            "binding_authority": False,
        }

    def list_connectors(self, body: dict[str, Any]) -> dict[str, Any]:
        return self.connectors(body)

    def messages(self, body: dict[str, Any]) -> dict[str, Any]:
        tenant_id = identifier(body.get("tenant_id"), "tenant_id")
        connector_id = body.get("connector_id")
        return {
            "items": self.store.list_messages(
                tenant_id,
                connector_id=(
                    identifier(connector_id, "connector_id")
                    if connector_id is not None
                    else None
                ),
                direction=body.get("direction"),
                limit=int(body.get("limit", 100)),
            ),
            "binding_authority": False,
        }

    def list_messages(self, body: dict[str, Any]) -> dict[str, Any]:
        return self.messages(body)

    def audit(self, body: dict[str, Any]) -> dict[str, Any]:
        tenant_id = identifier(body.get("tenant_id"), "tenant_id")
        return {
            "items": self.store.audit_events(tenant_id),
            "chain_valid": self.store.verify_audit_chain(),
            "binding_authority": False,
        }

    def capabilities(self) -> dict[str, Any]:
        return {
            "schema_version": "edon-agent-gateway-capabilities.v1",
            "protocol_versions": dict(PROTOCOL_VERSIONS),
            "connector_modes": ["READ_ONLY", "SHADOW"],
            "ingress_status": "ACCEPTED_SHADOW_ONLY",
            "egress_status": "STAGED_NOT_DELIVERED",
            "delivery_worker_implemented": False,
            "direct_execution": False,
            "binding_authority": False,
        }

    def vendors(self) -> dict[str, Any]:
        items = vendor_profiles()
        return {
            "schema_version": "edon-agent-gateway-vendors.v1",
            "items": items,
            "count": len(items),
            "certification_claim": False,
            "binding_authority": False,
        }

    def counts(self) -> dict[str, int]:
        return self.store.counts()