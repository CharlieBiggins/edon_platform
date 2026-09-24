"""Append-only cross-component provenance graph for the Cerebrum System."""

from __future__ import annotations

import json
from copy import deepcopy
from datetime import UTC, datetime
from typing import Any

from edon.common.hashing import sha256_json


NODE_TYPES = {
    "SOURCE",
    "STATE_ASSERTION",
    "STATE_PROJECTION",
    "C1_INFERENCE",
    "PLAN",
    "OPTIMIZATION_CANDIDATE",
    "AUTHORIZATION",
    "COMMIT",
    "OUTCOME",
    "ACTIONNET_EXPERIENCE",
    "ARTIFACT",
}
RELATIONS = {
    "DERIVED_FROM",
    "INFORMED",
    "PROPOSED",
    "OPTIMIZED",
    "AUTHORIZED",
    "COMMITTED",
    "RESULTED_IN",
    "CAPTURED_AS",
    "CONTESTS",
}
EVIDENCE_STATUSES = {"DECLARED", "OBSERVED_ORDER", "INTERVENTION_VERIFIED", "CONTESTED"}


class ProvenanceGraphError(RuntimeError):
    """Raised when provenance identity or graph invariants are violated."""


def _identifier(value: Any, label: str) -> str:
    normalized = str(value or "").strip()
    if not normalized or len(normalized) > 240:
        raise ProvenanceGraphError(f"{label} must contain between 1 and 240 characters")
    return normalized


def _sha256(value: Any, label: str) -> str:
    normalized = str(value or "").strip()
    if not normalized.startswith("sha256:") or len(normalized) != 71:
        raise ProvenanceGraphError(f"{label} must be a prefixed SHA-256 digest")
    try:
        int(normalized.split(":", 1)[1], 16)
    except ValueError as exc:
        raise ProvenanceGraphError(f"{label} must be a prefixed SHA-256 digest") from exc
    return normalized


def _timestamp(value: Any, label: str) -> str:
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError as exc:
        raise ProvenanceGraphError(f"{label} must be an ISO-8601 timestamp") from exc
    if parsed.tzinfo is None:
        raise ProvenanceGraphError(f"{label} must include a timezone")
    return parsed.astimezone(UTC).isoformat()


def _metadata(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ProvenanceGraphError("metadata must be an object")
    try:
        json.dumps(value, allow_nan=False)
    except (TypeError, ValueError) as exc:
        raise ProvenanceGraphError("metadata must contain finite JSON values") from exc
    return deepcopy(value)


class CausalProvenanceGraph:
    """Record lineage and evidence status without inferring causal truth."""

    def __init__(self, tenant_id: str, world_id: str):
        self.tenant_id = _identifier(tenant_id, "tenant_id")
        self.world_id = _identifier(world_id, "world_id")
        self._nodes: dict[str, dict[str, Any]] = {}
        self._edges: dict[str, dict[str, Any]] = {}

    def record_node(
        self,
        node_id: str,
        node_type: str,
        payload_sha256: str,
        *,
        occurred_at: str,
        available_to_controller_at: str,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        normalized_type = str(node_type).upper()
        if normalized_type not in NODE_TYPES:
            raise ProvenanceGraphError(f"unsupported provenance node type: {normalized_type}")
        normalized_occurred_at = _timestamp(occurred_at, "occurred_at")
        normalized_available_at = _timestamp(
            available_to_controller_at, "available_to_controller_at"
        )
        if normalized_occurred_at > normalized_available_at:
            raise ProvenanceGraphError(
                "available_to_controller_at cannot precede occurred_at"
            )
        core = {
            "schema_version": "edon-causal-provenance-node.v1",
            "node_id": _identifier(node_id, "node_id"),
            "tenant_id": self.tenant_id,
            "world_id": self.world_id,
            "node_type": normalized_type,
            "payload_sha256": _sha256(payload_sha256, "payload_sha256"),
            "occurred_at": normalized_occurred_at,
            "available_to_controller_at": normalized_available_at,
            "metadata": _metadata(metadata or {}),
            "binding_authority": False,
        }
        node = {**core, "node_sha256": sha256_json(core)}
        existing = self._nodes.get(node["node_id"])
        if existing:
            if existing["node_sha256"] != node["node_sha256"]:
                raise ProvenanceGraphError("node_id is already bound to different content")
            return deepcopy(existing)
        self._nodes[node["node_id"]] = node
        return deepcopy(node)

    def _reachable(self, source_id: str, target_id: str) -> bool:
        adjacency: dict[str, set[str]] = {}
        for edge in self._edges.values():
            adjacency.setdefault(edge["source_node_id"], set()).add(edge["target_node_id"])
        pending = [source_id]
        seen: set[str] = set()
        while pending:
            current = pending.pop()
            if current == target_id:
                return True
            if current in seen:
                continue
            seen.add(current)
            pending.extend(sorted(adjacency.get(current, set()), reverse=True))
        return False

    def record_edge(
        self,
        edge_id: str,
        source_node_id: str,
        target_node_id: str,
        relation: str,
        *,
        evidence_status: str,
        evidence_refs: list[str],
        recorded_at: str,
    ) -> dict[str, Any]:
        source = _identifier(source_node_id, "source_node_id")
        target = _identifier(target_node_id, "target_node_id")
        if source not in self._nodes or target not in self._nodes:
            raise ProvenanceGraphError("provenance edge references an unknown node")
        if source == target or self._reachable(target, source):
            raise ProvenanceGraphError("provenance edge would create a cycle")
        normalized_relation = str(relation).upper()
        if normalized_relation not in RELATIONS:
            raise ProvenanceGraphError(f"unsupported provenance relation: {normalized_relation}")
        normalized_status = str(evidence_status).upper()
        if normalized_status not in EVIDENCE_STATUSES:
            raise ProvenanceGraphError(f"unsupported evidence status: {normalized_status}")
        refs = sorted({_identifier(item, "evidence_ref") for item in evidence_refs})
        if not refs:
            raise ProvenanceGraphError("at least one evidence_ref is required")
        core = {
            "schema_version": "edon-causal-provenance-edge.v1",
            "edge_id": _identifier(edge_id, "edge_id"),
            "tenant_id": self.tenant_id,
            "world_id": self.world_id,
            "source_node_id": source,
            "target_node_id": target,
            "relation": normalized_relation,
            "evidence_status": normalized_status,
            "evidence_refs": refs,
            "recorded_at": _timestamp(recorded_at, "recorded_at"),
            "binding_authority": False,
        }
        edge = {**core, "edge_sha256": sha256_json(core)}
        existing = self._edges.get(edge["edge_id"])
        if existing:
            if existing["edge_sha256"] != edge["edge_sha256"]:
                raise ProvenanceGraphError("edge_id is already bound to different content")
            return deepcopy(existing)
        self._edges[edge["edge_id"]] = edge
        return deepcopy(edge)

    def trace_paths(self, source_node_id: str, target_node_id: str, *, max_depth: int = 32) -> list[list[str]]:
        source = _identifier(source_node_id, "source_node_id")
        target = _identifier(target_node_id, "target_node_id")
        if source not in self._nodes or target not in self._nodes:
            raise ProvenanceGraphError("trace endpoint is not registered")
        adjacency: dict[str, list[str]] = {}
        for edge in sorted(self._edges.values(), key=lambda row: row["edge_id"]):
            adjacency.setdefault(edge["source_node_id"], []).append(edge["target_node_id"])
        paths: list[list[str]] = []

        def visit(current: str, path: list[str]) -> None:
            if len(path) > max_depth + 1:
                return
            if current == target:
                paths.append(path)
                return
            for candidate in adjacency.get(current, []):
                if candidate not in path:
                    visit(candidate, path + [candidate])

        visit(source, [source])
        return paths

    def snapshot(self) -> dict[str, Any]:
        core = {
            "schema_version": "edon-causal-provenance-graph.v1",
            "tenant_id": self.tenant_id,
            "world_id": self.world_id,
            "nodes": [deepcopy(self._nodes[key]) for key in sorted(self._nodes)],
            "edges": [deepcopy(self._edges[key]) for key in sorted(self._edges)],
            "causal_claim_boundary": "Recorded lineage and evidence status only; causal truth requires the declared validation method.",
            "binding_authority": False,
        }
        return {**core, "graph_sha256": sha256_json(core)}


__all__ = [
    "CausalProvenanceGraph",
    "EVIDENCE_STATUSES",
    "NODE_TYPES",
    "ProvenanceGraphError",
    "RELATIONS",
]