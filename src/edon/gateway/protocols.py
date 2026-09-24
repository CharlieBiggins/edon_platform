"""Protocol normalization for MCP, A2A, REST/webhooks, and FHIR R4/SMART."""

from __future__ import annotations

from typing import Any

from .models import AgentGatewayError


FHIR_READ_OPERATIONS = {"READ", "SEARCH", "EVENT"}
FHIR_WRITE_OPERATIONS = {"CREATE", "UPDATE", "PATCH", "DELETE", "TRANSACTION", "BATCH"}


def _common(request: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(request, dict):
        raise AgentGatewayError("gateway message request must be an object")
    body = request.get("body")
    if not isinstance(body, dict):
        raise AgentGatewayError("gateway message body must be an object")
    return {
        "message_id": request.get("message_id"),
        "idempotency_key": request.get("idempotency_key"),
        "occurred_at": request.get("occurred_at"),
        "sensitivity": request.get("sensitivity", "INTERNAL"),
        "trace_context": request.get("trace_context", {}),
        "body": body,
    }


def _allowed(profile: dict[str, Any], operation: str) -> None:
    if operation not in profile.get("allowed_operations", []):
        raise AgentGatewayError(f"operation is not allowlisted for connector: {operation}")


def _target_allowed(profile: dict[str, Any], target: str | None) -> None:
    allowed = profile.get("allowed_targets", [])
    if allowed and (not target or target not in allowed):
        raise AgentGatewayError(f"target is not allowlisted for connector: {target or '<missing>'}")


def normalize_mcp(profile: dict[str, Any], request: dict[str, Any]) -> dict[str, Any]:
    common = _common(request)
    body = common.pop("body")
    if body.get("jsonrpc") != "2.0":
        raise AgentGatewayError("MCP message must use JSON-RPC 2.0")
    method = str(body.get("method", ""))
    _allowed(profile, method)
    params = body.get("params", {})
    if not isinstance(params, dict):
        raise AgentGatewayError("MCP params must be an object")
    target = None
    if method == "tools/call":
        target = str(params.get("name", ""))
    elif method in {"resources/read", "prompts/get"}:
        target = str(params.get("uri") or params.get("name") or "")
    if method in {"tools/call", "resources/read", "prompts/get"}:
        _target_allowed(profile, target or None)
    return {
        **common,
        "message_type": "MCP_" + method.replace("/", "_").replace(".", "_").upper(),
        "payload": {"jsonrpc": "2.0", "id": body.get("id"), "method": method, "params": params},
    }


def normalize_a2a(profile: dict[str, Any], request: dict[str, Any]) -> dict[str, Any]:
    common = _common(request)
    body = common.pop("body")
    if "jsonrpc" in body and body.get("jsonrpc") != "2.0":
        raise AgentGatewayError("A2A JSON-RPC binding must use JSON-RPC 2.0")
    operation = str(body.get("operation") or body.get("method") or "")
    _allowed(profile, operation)
    target = body.get("skill_id") or body.get("target_skill")
    _target_allowed(profile, str(target) if target is not None else None)
    payload = body.get("params", body.get("payload", body))
    if not isinstance(payload, dict):
        raise AgentGatewayError("A2A operation payload must be an object")
    return {
        **common,
        "message_type": "A2A_" + operation.replace("/", "_").replace(".", "_").upper(),
        "payload": {"operation": operation, "payload": payload},
    }


def normalize_rest(profile: dict[str, Any], request: dict[str, Any]) -> dict[str, Any]:
    common = _common(request)
    body = common.pop("body")
    operation = str(body.get("operation", ""))
    _allowed(profile, operation)
    target = body.get("target")
    _target_allowed(profile, str(target) if target is not None else None)
    payload = body.get("payload", {})
    if not isinstance(payload, dict):
        raise AgentGatewayError("REST/webhook payload must be an object")
    return {
        **common,
        "message_type": f"{profile['protocol']}_{operation}".replace("/", "_").upper(),
        "payload": {"operation": operation, "target": target, "payload": payload},
    }


def normalize_fhir(profile: dict[str, Any], request: dict[str, Any]) -> dict[str, Any]:
    common = _common(request)
    body = common.pop("body")
    operation = str(body.get("operation", "")).upper()
    if operation in FHIR_WRITE_OPERATIONS:
        raise AgentGatewayError("FHIR writes are prohibited at the Agent Gateway boundary")
    if operation not in FHIR_READ_OPERATIONS:
        raise AgentGatewayError("FHIR gateway operation must be READ, SEARCH, or EVENT")
    _allowed(profile, operation)
    resource_type = str(body.get("resource_type", ""))
    _target_allowed(profile, resource_type or None)
    payload = body.get("payload", {})
    if not isinstance(payload, dict):
        raise AgentGatewayError("FHIR payload must be an object")
    return {
        **common,
        "message_type": f"FHIR_{operation}_{resource_type or 'RESOURCE'}".upper(),
        "payload": {
            "operation": operation,
            "resource_type": resource_type,
            "payload": payload,
            "write_permitted": False,
        },
    }


def normalize_protocol_message(profile: dict[str, Any], request: dict[str, Any]) -> dict[str, Any]:
    protocol = profile["protocol"]
    if protocol == "MCP":
        return normalize_mcp(profile, request)
    if protocol == "A2A":
        return normalize_a2a(profile, request)
    if protocol in {"REST", "WEBHOOK"}:
        return normalize_rest(profile, request)
    if protocol == "FHIR_R4_SMART":
        return normalize_fhir(profile, request)
    raise AgentGatewayError(f"no normalizer for protocol: {protocol}")