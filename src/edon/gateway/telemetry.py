"""Content-minimized OpenTelemetry-compatible gateway span generation."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from typing import Any
from urllib.parse import urlparse


def _attribute(key: str, value: Any) -> dict[str, Any]:
    if isinstance(value, bool):
        return {"key": key, "value": {"boolValue": value}}
    if isinstance(value, int):
        return {"key": key, "value": {"intValue": str(value)}}
    return {"key": key, "value": {"stringValue": str(value)}}


def _trace_ids(envelope: dict[str, Any]) -> tuple[str, str]:
    traceparent = envelope.get("trace_context", {}).get("traceparent", "")
    parts = traceparent.split("-")
    if len(parts) == 4:
        return parts[1], parts[2]
    digest = hashlib.sha256(envelope["envelope_sha256"].encode("utf-8")).hexdigest()
    return digest[:32], digest[32:48]


def otlp_span(envelope: dict[str, Any], *, endpoint: str, status: str) -> dict[str, Any]:
    """Return an OTLP/HTTP-JSON-compatible span without message contents."""

    trace_id, span_id = _trace_ids(envelope)
    occurred = datetime.fromisoformat(envelope["occurred_at"])
    timestamp = int(occurred.timestamp() * 1_000_000_000)
    payload_size = len(
        json.dumps(
            envelope.get("payload", {}), sort_keys=True, separators=(",", ":"),
            ensure_ascii=False,
        ).encode("utf-8")
    )
    attributes = [
        _attribute("service.name", "edon-agent-gateway"),
        _attribute("edon.gateway.connector.id", envelope["connector_id"]),
        _attribute("edon.gateway.vendor.id", envelope["vendor_id"]),
        _attribute("edon.gateway.protocol", envelope["protocol"]),
        _attribute("edon.gateway.protocol.version", envelope["protocol_version"]),
        _attribute("edon.gateway.direction", envelope["direction"]),
        _attribute("edon.gateway.message.type", envelope["message_type"]),
        _attribute("edon.gateway.message.sha256", envelope["envelope_sha256"]),
        _attribute("edon.gateway.sensitivity", envelope["sensitivity"]),
        _attribute("edon.gateway.status", status),
        _attribute("edon.gateway.executed", False),
        _attribute("edon.gateway.binding_authority", False),
        _attribute("edon.gateway.content_recorded", False),
        _attribute("edon.gateway.normalized_payload.bytes", payload_size),
        _attribute("gen_ai.operation.name", envelope["message_type"].lower()),
        _attribute("gen_ai.provider.name", envelope["vendor_id"]),
        _attribute("server.address", urlparse(endpoint).hostname or "unknown"),
    ]
    return {
        "resourceSpans": [
            {
                "resource": {
                    "attributes": [
                        _attribute("service.name", "edon-agent-gateway"),
                        _attribute("service.version", "0.5.1"),
                    ]
                },
                "scopeSpans": [
                    {
                        "scope": {"name": "edon.gateway", "version": "0.5.1"},
                        "spans": [
                            {
                                "traceId": trace_id,
                                "spanId": span_id,
                                "name": f"{envelope['direction'].lower()} {envelope['message_type']}",
                                "kind": 2 if envelope["direction"] == "INGRESS" else 3,
                                "startTimeUnixNano": str(timestamp),
                                "endTimeUnixNano": str(timestamp),
                                "attributes": attributes,
                                "status": {"code": 1, "message": status},
                            }
                        ],
                    }
                ],
            }
        ]
    }