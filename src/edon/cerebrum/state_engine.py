"""Deterministic multi-view institutional state projection for Cerebrum."""

from __future__ import annotations

import json
from copy import deepcopy
from datetime import UTC, datetime
from typing import Any

from edon.common.hashing import sha256_json


STATE_CLASSES = {"OBSERVED", "REPORTED", "INFERRED", "AUTHORIZED", "COMMITTED"}


class StateEngineError(RuntimeError):
    """Raised when an assertion violates state separation or time gating."""


def _identifier(value: Any, label: str) -> str:
    normalized = str(value or "").strip()
    if not normalized or len(normalized) > 200:
        raise StateEngineError(f"{label} must contain between 1 and 200 characters")
    return normalized


def _timestamp(value: Any, label: str) -> str:
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError as exc:
        raise StateEngineError(f"{label} must be an ISO-8601 timestamp") from exc
    if parsed.tzinfo is None:
        raise StateEngineError(f"{label} must include a timezone")
    return parsed.astimezone(UTC).isoformat()


def _json_value(value: Any, label: str) -> Any:
    try:
        json.dumps(value, allow_nan=False)
    except (TypeError, ValueError) as exc:
        raise StateEngineError(f"{label} must contain finite JSON values") from exc
    return deepcopy(value)


def _sha256(value: Any, label: str) -> str:
    normalized = str(value or "").strip()
    if not normalized.startswith("sha256:") or len(normalized) != 71:
        raise StateEngineError(f"{label} must be a prefixed SHA-256 digest")
    try:
        int(normalized.split(":", 1)[1], 16)
    except ValueError as exc:
        raise StateEngineError(f"{label} must be a prefixed SHA-256 digest") from exc
    return normalized


def _state_path(value: Any) -> list[str]:
    if not isinstance(value, (list, tuple)) or not value:
        raise StateEngineError("state_path must be a non-empty array")
    return [_identifier(item, "state_path item") for item in value]


def _path_key(path: list[str]) -> str:
    """Encode a state path as an unambiguous JSON Pointer."""

    return "/" + "/".join(item.replace("~", "~0").replace("/", "~1") for item in path)


class InstitutionalStateEngine:
    """Keep evidence and authority state classes separate under a decision clock.

    This reference projector never commits world state. It deterministically
    selects the latest eligible assertion within each state class and path while
    preserving the complete eligible assertion history and same-time conflicts.
    """

    def __init__(self, tenant_id: str, world_id: str):
        self.tenant_id = _identifier(tenant_id, "tenant_id")
        self.world_id = _identifier(world_id, "world_id")
        self._assertions: dict[str, dict[str, Any]] = {}

    def ingest(self, assertion: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(assertion, dict):
            raise StateEngineError("state assertion must be an object")
        if assertion.get("binding_authority") not in {None, False}:
            raise StateEngineError("a state assertion cannot carry binding authority")
        tenant_id = _identifier(assertion.get("tenant_id", self.tenant_id), "tenant_id")
        world_id = _identifier(assertion.get("world_id", self.world_id), "world_id")
        if tenant_id != self.tenant_id or world_id != self.world_id:
            raise StateEngineError("state assertion tenant or world does not match the engine")
        state_class = str(assertion.get("state_class", "")).upper()
        if state_class not in STATE_CLASSES:
            raise StateEngineError(f"unsupported state_class: {state_class or '<missing>'}")
        occurred_at = _timestamp(assertion.get("occurred_at"), "occurred_at")
        recorded_at = _timestamp(assertion.get("recorded_at"), "recorded_at")
        available_at = _timestamp(
            assertion.get("available_to_controller_at"), "available_to_controller_at"
        )
        if occurred_at > recorded_at:
            raise StateEngineError("recorded_at cannot precede occurred_at")
        if recorded_at > available_at:
            raise StateEngineError("available_to_controller_at cannot precede recorded_at")
        confidence = assertion.get("confidence")
        if isinstance(confidence, bool) or not isinstance(confidence, (int, float)):
            raise StateEngineError("confidence must be numeric")
        confidence = float(confidence)
        if not 0 <= confidence <= 1:
            raise StateEngineError("confidence must be between 0 and 1")

        model_lineage = assertion.get("model_lineage")
        authorization_ref_sha256 = assertion.get("authorization_ref_sha256")
        world_version = assertion.get("world_version")
        committed_state_sha256 = assertion.get("committed_state_sha256")
        if state_class == "INFERRED" and not str(model_lineage or "").strip():
            raise StateEngineError("INFERRED state requires model_lineage")
        if state_class in {"AUTHORIZED", "COMMITTED"}:
            authorization_ref_sha256 = _sha256(
                authorization_ref_sha256, "authorization_ref_sha256"
            )
        if state_class == "COMMITTED":
            if isinstance(world_version, bool) or not isinstance(world_version, int) or world_version < 0:
                raise StateEngineError("COMMITTED state requires a non-negative world_version")
            committed_state_sha256 = _sha256(
                committed_state_sha256, "committed_state_sha256"
            )

        core: dict[str, Any] = {
            "schema_version": "edon-cerebrum-state-assertion.v1",
            "assertion_id": _identifier(assertion.get("assertion_id"), "assertion_id"),
            "tenant_id": tenant_id,
            "world_id": world_id,
            "state_class": state_class,
            "state_path": _state_path(assertion.get("state_path")),
            "value": _json_value(assertion.get("value"), "value"),
            "occurred_at": occurred_at,
            "recorded_at": recorded_at,
            "available_to_controller_at": available_at,
            "source_ref": _identifier(assertion.get("source_ref"), "source_ref"),
            "confidence": confidence,
            "provenance": _json_value(assertion.get("provenance", {}), "provenance"),
            "binding_authority": False,
        }
        if model_lineage is not None:
            core["model_lineage"] = _identifier(model_lineage, "model_lineage")
        if authorization_ref_sha256 is not None:
            core["authorization_ref_sha256"] = authorization_ref_sha256
        if world_version is not None:
            core["world_version"] = world_version
        if committed_state_sha256 is not None:
            core["committed_state_sha256"] = committed_state_sha256
        normalized = {**core, "assertion_sha256": sha256_json(core)}
        existing = self._assertions.get(normalized["assertion_id"])
        if existing:
            if existing["assertion_sha256"] != normalized["assertion_sha256"]:
                raise StateEngineError("assertion_id is already bound to different content")
            return deepcopy(existing)
        self._assertions[normalized["assertion_id"]] = normalized
        return deepcopy(normalized)

    def project(self, decision_time: str) -> dict[str, Any]:
        clock = _timestamp(decision_time, "decision_time")
        eligible = sorted(
            (
                deepcopy(row)
                for row in self._assertions.values()
                if row["available_to_controller_at"] <= clock
            ),
            key=lambda row: (
                row["available_to_controller_at"],
                row["occurred_at"],
                row["assertion_id"],
            ),
        )
        views: dict[str, dict[str, dict[str, Any]]] = {
            state_class: {} for state_class in sorted(STATE_CLASSES)
        }
        grouped: dict[tuple[str, str], list[dict[str, Any]]] = {}
        for row in eligible:
            path = _path_key(row["state_path"])
            views[row["state_class"]][path] = row
            grouped.setdefault((row["state_class"], path), []).append(row)

        conflicts: list[dict[str, Any]] = []
        for (state_class, path), rows in sorted(grouped.items()):
            latest_time = max(row["available_to_controller_at"] for row in rows)
            latest = [row for row in rows if row["available_to_controller_at"] == latest_time]
            value_hashes = {sha256_json(row["value"]) for row in latest}
            if len(value_hashes) > 1:
                conflicts.append(
                    {
                        "state_class": state_class,
                        "state_path": latest[0]["state_path"],
                        "assertion_ids": sorted(row["assertion_id"] for row in latest),
                        "available_to_controller_at": latest_time,
                    }
                )

        core = {
            "schema_version": "edon-cerebrum-state-projection.v1",
            "tenant_id": self.tenant_id,
            "world_id": self.world_id,
            "decision_time": clock,
            "assertions": eligible,
            "views": views,
            "conflicts": conflicts,
            "separated_state_classes": True,
            "future_assertions_excluded": len(self._assertions) - len(eligible),
            "binding_authority": False,
        }
        return {**core, "projection_sha256": sha256_json(core)}

    def count(self) -> int:
        return len(self._assertions)


__all__ = ["InstitutionalStateEngine", "STATE_CLASSES", "StateEngineError"]