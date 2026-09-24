"""Vendor-neutral, non-binding EDON Agent Gateway."""

from .models import AgentGatewayError, ConnectorProfile, GatewayEnvelope, PROTOCOL_VERSIONS
from .service import AgentGateway
from .store import AgentGatewayStore
from .telemetry import otlp_span
from .vendors import VENDOR_PROFILES, vendor_profiles

__all__ = [
    "AgentGateway",
    "AgentGatewayError",
    "AgentGatewayStore",
    "ConnectorProfile",
    "GatewayEnvelope",
    "PROTOCOL_VERSIONS",
    "VENDOR_PROFILES",
    "otlp_span",
    "vendor_profiles",
]