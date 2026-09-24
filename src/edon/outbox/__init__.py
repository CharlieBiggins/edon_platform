"""Durable transactional outbox for world-event delivery."""

from .store import OutboxError, TransactionalOutbox

__all__ = ["OutboxError", "TransactionalOutbox"]