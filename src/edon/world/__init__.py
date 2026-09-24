"""Persistent, event-sourced institutional world state."""

from .store import WorldStateError, WorldStateStore

__all__ = ["WorldStateError", "WorldStateStore"]