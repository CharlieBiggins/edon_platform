"""Kernel-authorized wrapper around the event-sourced institutional world."""

from __future__ import annotations

from typing import Any, Iterable

from edon.world import WorldStateStore

from .tokens import KernelTokenAuthority


class KernelAuthorizedWorld:
    """Commits only requests carrying an exact, valid Kernel execution token."""

    def __init__(self, worlds: WorldStateStore, authority: KernelTokenAuthority):
        self.worlds = worlds
        self.authority = authority

    def create_world(
        self,
        tenant_id: str,
        world_id: str,
        initial_state: dict[str, Any],
        *,
        actor_id: str,
        authority_version: str,
        execution_token: str,
        source_lineage: Iterable[str] = (),
        timestamp: str | None = None,
    ) -> dict[str, Any]:
        mutations = [{"op": "REPLACE_ROOT", "path": [], "value": initial_state}]
        existing_event = None
        try:
            existing_event = next(
                row for row in self.worlds.events(tenant_id, world_id)
                if row["event_id"] == "WORLD_CREATED"
            )
        except (StopIteration, RuntimeError):
            existing_event = None
        self.authority.verify_world_event(
            execution_token,
            tenant_id=tenant_id,
            world_id=world_id,
            actor_id=actor_id,
            authority_version=authority_version,
            expected_world_version=-1,
            event_id="WORLD_CREATED",
            event_type="WORLD_CREATED",
            mutations=mutations,
            allow_consumed=existing_event is not None,
            expected_event_hash=existing_event["event_hash"] if existing_event else None,
        )
        snapshot = self.worlds.create_world(
            tenant_id, world_id, initial_state,
            actor_id=actor_id, authorization_ref=execution_token,
            source_lineage=source_lineage, timestamp=timestamp,
        )
        self.authority.consume(
            execution_token,
            event_identity=f"{tenant_id}:{world_id}:WORLD_CREATED",
            event_hash=str(snapshot["event_hash"]),
        )
        return snapshot

    def append_event(
        self,
        tenant_id: str,
        world_id: str,
        event_id: str,
        event_type: str,
        mutations: Iterable[dict[str, Any]],
        *,
        actor_id: str,
        authority_version: str,
        expected_version: int,
        execution_token: str,
        source_lineage: Iterable[str] = (),
        timestamp: str | None = None,
    ) -> dict[str, Any]:
        normalized = list(mutations)
        existing_event = None
        try:
            existing_event = next(
                row for row in self.worlds.events(tenant_id, world_id)
                if row["event_id"] == event_id
            )
        except (StopIteration, RuntimeError):
            existing_event = None
        self.authority.verify_world_event(
            execution_token,
            tenant_id=tenant_id, world_id=world_id, actor_id=actor_id,
            authority_version=authority_version,
            expected_world_version=expected_version,
            event_id=event_id, event_type=event_type, mutations=normalized,
            allow_consumed=existing_event is not None,
            expected_event_hash=existing_event["event_hash"] if existing_event else None,
        )
        snapshot = self.worlds.append_event(
            tenant_id, world_id, event_id, event_type, normalized,
            actor_id=actor_id, expected_version=expected_version,
            authorization_ref=execution_token, source_lineage=source_lineage,
            timestamp=timestamp,
        )
        self.authority.consume(
            execution_token,
            event_identity=f"{tenant_id}:{world_id}:{event_id}",
            event_hash=str(snapshot["event_hash"]),
        )
        return snapshot