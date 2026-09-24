"""Typed contracts and security validation for the EDON Agent Gateway."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from urllib.parse import urlparse

from edon.common.hashing import sha256_json


PROTOCOL_VERSIONS = {
    "MCP": "2026-07-28",
    "A2A": "1.0",
    "REST": "1.0",
    "WEBHOOK": "1.0",
    "FHIR_R4_SMART": "R4",
}

CONNECTOR_MODES = {"SHADOW", "READ_ONLY"}
CONNECTOR_STATUSES = {"DISABLED", "ENABLED", "SUSPENDED"}
AUTH_METHODS = {
    "OAUTH2_CLIENT_CREDENTIALS",
    "OAUTH2_AUTHORIZATION_CODE",
    "API_KEY",
    "MTLS",
    "SMART_BACKEND_SERVICES",
    "SMART_USER",
    "NONE_DEV_ONLY",
}
SENSITIVITIES = {"PUBLIC", "INTERNAL", "CONFIDENTIAL", "RESTRICTED"}
MAX_GATEWAY_PAYLOAD_BYTES = 1_048_576

_IDENTIFIER = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
_TRACEPARENT = re.compile(r"^[0-9a-f]{2}-[0-9a-f]{32}-[0-9a-f]{16}-[0-9a-f]{2}$")

CREDENTIAL_VALUE_FIELDS = {
    "access_token",
    "refresh_token",
    "client_secret",
    "api_key",
    "password",
    "private_key",
    "bearer_token",
}
AUTHORITY_FIELDS = {
    "authorization_ref",
    "execution_token",
    "kernel_token",
    "binding_eligible",
    "commit",
    "committed",
}


class AgentGatewayError(RuntimeError):
    """Raised when a connector or message violates a gateway invariant."""


def identifier(value: Any, field: str) -> str:
    normalized = str(value or "").strip()
    if not _IDENTIFIER.fullmatch(normalized):
        raise AgentGatewayError(
            f"{field} must contain 1-128 letters, digits, dots, underscores, colons, or hyphens"
        )
    return normalized


def utc_timestamp(value: Any, field: str = "occurred_at") -> str:
    normalized = str(value or "").strip()
    if not normalized:
        raise AgentGatewayError(f"{field} is required")
    try:
        parsed = datetime.fromisoformat(normalized.replace("Z", "+00:00"))
    except ValueError as exc:
        raise AgentGatewayError(f"{field} must be an ISO-8601 timestamp") from exc
    if parsed.tzinfo is None:
        raise AgentGatewayError(f"{field} must include a timezone")
    return parsed.astimezone(UTC).isoformat()


def https_endpoint(value: Any) -> str:
    endpoint = str(value or "").strip()
    parsed = urlparse(endpoint)
    if parsed.scheme != "https" or not parsed.hostname:
        raise AgentGatewayError("connector endpoint must be an absolute HTTPS URL")
    if parsed.username or parsed.password:
        raise AgentGatewayError("connector endpoint must not contain credentials")
    if parsed.fragment:
        raise AgentGatewayError("connector endpoint must not contain a fragment")
    return endpoint


def _unsafe_paths(value: Any, prefix: str = "") -> list[str]:
    paths: list[str] = []
    if isinstance(value, dict):
        for raw_key, child in value.items():
            key = str(raw_key)
            path = f"{prefix}.{key}" if prefix else key
            lowered = key.lower()
            if lowered in CREDENTIAL_VALUE_FIELDS or lowered in AUTHORITY_FIELDS:
                paths.append(path)
            if lowered == "binding_authority" and child is not False:
                paths.append(path)
            paths.extend(_unsafe_paths(child, path))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            paths.extend(_unsafe_paths(child, f"{prefix}[{index}]"))
    return paths


def validate_untrusted_payload(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise AgentGatewayError("gateway payload must be a JSON object")
    paths = sorted(set(_unsafe_paths(payload)))
    if paths:
        raise AgentGatewayError(
            "gateway payload contains credential or authority fields: " + ", ".join(paths)
        )
    encoded = json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")
    if len(encoded) > MAX_GATEWAY_PAYLOAD_BYTES:
        raise AgentGatewayError("gateway payload exceeds the 1 MiB normalized limit")
    return payload


def validate_trace_context(value: Any) -> dict[str, str]:
    if value is None or value == "":
        return {}
    if not isinstance(value, dict):
        raise AgentGatewayError("trace_context must be an object")
    extra = set(value) - {"traceparent", "tracestate"}
    if extra:
        raise AgentGatewayError("trace_context may contain traceparent and tracestate only")
    traceparent = str(value.get("traceparent", "")).lower()
    if traceparent and not _TRACEPARENT.fullmatch(traceparent):
        raise AgentGatewayError("traceparent is not valid W3C trace context")
    tracestate = str(value.get("tracestate", ""))
    if len(tracestate.encode("utf-8")) > 512:
        raise AgentGatewayError("tracestate exceeds 512 bytes")
    return {
        key: item
        for key, item in {"traceparent": traceparent, "tracestate": tracestate}.items()
        if item
    }


@dataclass(frozen=True)
class ConnectorProfile:
    connector_id: str
    tenant_id: str
    vendor_id: str
    protocol: str
    protocol_version: str
    endpoint: str
    auth_method: str
    credential_secret_ref: str
    allowed_operations: tuple[str, ...]
    allowed_targets: tuple[str, ...]
    mode: str
    sensitivity_ceiling: str
    data_residency: str
    enabled: bool = False
    binding_authority: bool = False

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "ConnectorProfile":
        if not isinstance(value, dict):
            raise AgentGatewayError("connector profile must be an object")
        forbidden = CREDENTIAL_VALUE_FIELDS & {str(key).lower() for key in value}
        if forbidden:
            raise AgentGatewayError(
                "connector profile must reference a secret manager and cannot contain: "
                + ", ".join(sorted(forbidden))
            )
        protocol = str(value.get("protocol", "")).upper()
        if protocol not in PROTOCOL_VERSIONS:
            raise AgentGatewayError(f"unsupported gateway protocol: {protocol or '<missing>'}")
        version = str(value.get("protocol_version", ""))
        if version != PROTOCOL_VERSIONS[protocol]:
            raise AgentGatewayError(
                f"{protocol} connector must target protocol version {PROTOCOL_VERSIONS[protocol]}"
            )
        auth_method = str(value.get("auth_method", "")).upper()
        if auth_method not in AUTH_METHODS:
            raise AgentGatewayError("unsupported connector auth_method")
        secret_ref = str(value.get("credential_secret_ref", "")).strip()
        if secret_ref and not secret_ref.startswith("secret://"):
            raise AgentGatewayError("credential_secret_ref must use the secret:// reference scheme")
        mode = str(value.get("mode", "SHADOW")).upper()
        if mode not in CONNECTOR_MODES:
            raise AgentGatewayError("connectors may operate only in SHADOW or READ_ONLY mode")
        sensitivity = str(value.get("sensitivity_ceiling", "INTERNAL")).upper()
        if sensitivity not in SENSITIVITIES:
            raise AgentGatewayError("unsupported sensitivity ceiling")
        operations = tuple(str(item) for item in value.get("allowed_operations", []))
        if not operations or any(not item.strip() for item in operations):
            raise AgentGatewayError("allowed_operations must contain at least one operation")
        if len(set(operations)) != len(operations):
            raise AgentGatewayError("allowed_operations must be unique")
        targets = tuple(str(item) for item in value.get("allowed_targets", []))
        if any(not item.strip() for item in targets) or len(set(targets)) != len(targets):
            raise AgentGatewayError("allowed_targets must contain unique non-empty values")
        if value.get("enabled") is True:
            raise AgentGatewayError("new connectors must be registered disabled")
        if value.get("binding_authority") not in {None, False}:
            raise AgentGatewayError("gateway connector cannot carry binding authority")
        return cls(
            connector_id=identifier(value.get("connector_id"), "connector_id"),
            tenant_id=identifier(value.get("tenant_id"), "tenant_id"),
            vendor_id=identifier(value.get("vendor_id"), "vendor_id"),
            protocol=protocol,
            protocol_version=version,
            endpoint=https_endpoint(value.get("endpoint")),
            auth_method=auth_method,
            credential_secret_ref=secret_ref,
            allowed_operations=operations,
            allowed_targets=targets,
            mode=mode,
            sensitivity_ceiling=sensitivity,
            data_residency=str(value.get("data_residency", "UNSPECIFIED")).strip()
            or "UNSPECIFIED",
            enabled=False,
            binding_authority=False,
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema_version": "edon-agent-gateway-connector.v1",
            "connector_id": self.connector_id,
            "tenant_id": self.tenant_id,
            "vendor_id": self.vendor_id,
            "protocol": self.protocol,
            "protocol_version": self.protocol_version,
            "endpoint": self.endpoint,
            "auth_method": self.auth_method,
            "credential_secret_ref": self.credential_secret_ref,
            "allowed_operations": list(self.allowed_operations),
            "allowed_targets": list(self.allowed_targets),
            "mode": self.mode,
            "sensitivity_ceiling": self.sensitivity_ceiling,
            "data_residency": self.data_residency,
            "enabled": False,
            "binding_authority": False,
        }


@dataclass(frozen=True)
class GatewayEnvelope:
    message_id: str
    tenant_id: str
    connector_id: str
    vendor_id: str
    protocol: str
    protocol_version: str
    direction: str
    message_type: str
    occurred_at: str
    idempotency_key: str
    sensitivity: str
    trace_context: dict[str, str]
    payload: dict[str, Any]
    binding_authority: bool = False
    executed: bool = False

    @classmethod
    def create(
        cls,
        *,
        profile: dict[str, Any],
        direction: str,
        message_id: Any,
        message_type: Any,
        occurred_at: Any,
        idempotency_key: Any,
        sensitivity: Any,
        trace_context: Any,
        payload: Any,
    ) -> "GatewayEnvelope":
        normalized_direction = str(direction).upper()
        if normalized_direction not in {"INGRESS", "EGRESS"}:
            raise AgentGatewayError("gateway direction must be INGRESS or EGRESS")
        normalized_sensitivity = str(sensitivity or "INTERNAL").upper()
        if normalized_sensitivity not in SENSITIVITIES:
            raise AgentGatewayError("unsupported gateway message sensitivity")
        ranking = ["PUBLIC", "INTERNAL", "CONFIDENTIAL", "RESTRICTED"]
        if ranking.index(normalized_sensitivity) > ranking.index(profile["sensitivity_ceiling"]):
            raise AgentGatewayError("message sensitivity exceeds connector ceiling")
        return cls(
            message_id=identifier(message_id, "message_id"),
            tenant_id=identifier(profile["tenant_id"], "tenant_id"),
            connector_id=identifier(profile["connector_id"], "connector_id"),
            vendor_id=identifier(profile["vendor_id"], "vendor_id"),
            protocol=str(profile["protocol"]),
            protocol_version=str(profile["protocol_version"]),
            direction=normalized_direction,
            message_type=identifier(message_type, "message_type"),
            occurred_at=utc_timestamp(occurred_at),
            idempotency_key=identifier(idempotency_key, "idempotency_key"),
            sensitivity=normalized_sensitivity,
            trace_context=validate_trace_context(trace_context),
            payload=validate_untrusted_payload(payload),
            binding_authority=False,
            executed=False,
        )

    def as_dict(self) -> dict[str, Any]:
        core = {
            "schema_version": "edon-agent-gateway-envelope.v1",
            "message_id": self.message_id,
            "tenant_id": self.tenant_id,
            "connector_id": self.connector_id,
            "vendor_id": self.vendor_id,
            "protocol": self.protocol,
            "protocol_version": self.protocol_version,
            "direction": self.direction,
            "message_type": self.message_type,
            "occurred_at": self.occurred_at,
            "idempotency_key": self.idempotency_key,
            "sensitivity": self.sensitivity,
            "trace_context": self.trace_context,
            "payload": self.payload,
            "binding_authority": False,
            "executed": False,
        }
        return {**core, "envelope_sha256": sha256_json(core)}