"""Governed institutional operations built on durable world state and memory."""

from .control import InstitutionalControlPlane, OperationsError

__all__ = ["InstitutionalControlPlane", "OperationsError"]