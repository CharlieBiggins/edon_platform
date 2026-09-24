"""Canonical Institutional IR and bounded human-behavior scenarios for ActionNet."""

from __future__ import annotations

import json
import math
import random
from copy import deepcopy
from datetime import datetime
from typing import Any

from edon.common.hashing import sha256_json


class InstitutionalIRError(ValueError):
    """Raised when an Institutional IR document violates the canonical contract."""


OBJECT_TYPES = {
    "INSTITUTION",
    "ENTITY",
    "ACTOR",
    "ROLE",
    "AUTHORITY",
    "CAPABILITY",
    "RESOURCE",
    "GOAL",
    "OBLIGATION",
    "POLICY",
    "EVIDENCE",
    "WORKFLOW",
    "PLAN",
    "DEPENDENCY",
    "EVENT",
    "ACTION",
    "OUTCOME",
    "RISK",
    "TEMPORAL_CONSTRAINT",
    "CONFLICT",
}

TUPLE_MAPPING = {
    "INSTITUTION": "X",
    "ENTITY": "X",
    "ACTOR": "X",
    "ROLE": "X",
    "CAPABILITY": "X",
    "EVIDENCE": "E",
    "RESOURCE": "R",
    "AUTHORITY": "A",
    "GOAL": "P",
    "OBLIGATION": "P",
    "POLICY": "P",
    "WORKFLOW": "W",
    "PLAN": "W",
    "DEPENDENCY": "W",
    "TEMPORAL_CONSTRAINT": "T",
    "CONFLICT": "C",
    "EVENT": "SIGMA",
    "ACTION": "SIGMA",
    "OUTCOME": "SIGMA",
    "RISK": "SIGMA",
}

EPISTEMIC_STATUSES = {
    "KNOWN",
    "UNKNOWN",
    "ESTIMATED",
    "STALE",
    "CONTRADICTORY",
    "DELAYED",
    "UNTRUSTED",
    "PROBABILISTIC",
}

STRATEGIC_BEHAVIORS = {
    "COOPERATIVE",
    "NEUTRAL",
    "COMPETITIVE",
    "OPPORTUNISTIC",
    "ADVERSARIAL",
}

NON_ACTIONABLE_EPISTEMIC = {
    "UNKNOWN", "STALE", "CONTRADICTORY", "DELAYED", "UNTRUSTED"
}


def _identifier(value: Any, label: str) -> str:
    if value is None:
        raise InstitutionalIRError(f"{label} is required")
    result = str(value).strip()
    if not result or len(result) > 200:
        raise InstitutionalIRError(f"{label} must contain between 1 and 200 characters")
    return result


def _json(value: Any, label: str) -> Any:
    try:
        encoded = json.dumps(value, allow_nan=False)
    except (TypeError, ValueError) as exc:
        raise InstitutionalIRError(f"{label} must contain finite JSON values") from exc
    return json.loads(encoded)


def _probability(value: Any, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise InstitutionalIRError(f"{label} must be numeric")
    result = float(value)
    if not math.isfinite(result) or not 0 <= result <= 1:
        raise InstitutionalIRError(f"{label} must be between 0 and 1")
    return result


def _iso_or_none(value: Any, label: str) -> str | None:
    if value is None:
        return None
    result = str(value)
    try:
        datetime.fromisoformat(result.replace("Z", "+00:00"))
    except ValueError as exc:
        raise InstitutionalIRError(f"{label} must be an ISO-8601 timestamp") from exc
    return result


def _normalize_epistemic(raw: Any, *, object_type: str) -> dict[str, Any]:
    if raw is None:
        raw = {}
    if not isinstance(raw, dict):
        raise InstitutionalIRError("epistemic_state must be an object")
    default_status = "UNKNOWN" if object_type == "EVIDENCE" else "KNOWN"
    status = str(raw.get("status", default_status)).upper()
    if status not in EPISTEMIC_STATUSES:
        raise InstitutionalIRError(f"unsupported epistemic status: {status}")
    default_confidence = 0.0 if status == "UNKNOWN" else 1.0 if status == "KNOWN" else 0.5
    confidence = _probability(raw.get("confidence", default_confidence), "epistemic confidence")
    if status == "UNKNOWN" and confidence != 0:
        raise InstitutionalIRError("UNKNOWN epistemic state must have zero confidence")
    if status == "PROBABILISTIC" and confidence in {0.0, 1.0}:
        raise InstitutionalIRError("PROBABILISTIC epistemic state requires confidence between 0 and 1")
    sources = sorted({_identifier(item, "epistemic source") for item in raw.get("sources", [])})
    return {
        "status": status,
        "confidence": confidence,
        "as_of": _iso_or_none(raw.get("as_of"), "epistemic as_of"),
        "sources": sources,
        "critical": bool(raw.get("critical", object_type == "EVIDENCE")),
    }


def _normalize_temporal(raw: Any) -> dict[str, Any]:
    if raw is None:
        raw = {}
    if not isinstance(raw, dict):
        raise InstitutionalIRError("temporal_state must be an object")
    valid_from = int(raw.get("valid_from_seconds", 0))
    valid_until_raw = raw.get("valid_until_seconds")
    valid_until = int(valid_until_raw) if valid_until_raw is not None else None
    observed_at = int(raw.get("observed_at_seconds", valid_from))
    if min(valid_from, observed_at) < 0 or (valid_until is not None and valid_until < valid_from):
        raise InstitutionalIRError("temporal bounds must be non-negative and ordered")
    return {
        "valid_from_seconds": valid_from,
        "valid_until_seconds": valid_until,
        "observed_at_seconds": observed_at,
    }


def _normalize_behavior(raw: Any) -> dict[str, Any]:
    if raw is None:
        raw = {}
    if not isinstance(raw, dict):
        raise InstitutionalIRError("behavior_model must be an object")
    strategic = str(raw.get("strategic_behavior", "NEUTRAL")).upper()
    if strategic not in STRATEGIC_BEHAVIORS:
        raise InstitutionalIRError(f"unsupported strategic behavior: {strategic}")
    trust_raw = raw.get("trust", {})
    if not isinstance(trust_raw, dict):
        raise InstitutionalIRError("behavior trust must be an object")
    trust = {
        _identifier(key, "trust target"): _probability(value, "trust value")
        for key, value in sorted(trust_raw.items())
    }
    return {
        "objectives": sorted({_identifier(item, "behavior objective") for item in raw.get("objectives", [])}),
        "incentives": sorted({_identifier(item, "behavior incentive") for item in raw.get("incentives", [])}),
        "trust": trust,
        "fatigue": _probability(raw.get("fatigue", 0.0), "fatigue"),
        "risk_tolerance": _probability(raw.get("risk_tolerance", 0.5), "risk_tolerance"),
        "information_access": sorted({_identifier(item, "information access") for item in raw.get("information_access", [])}),
        "cooperation_probability": _probability(
            raw.get("cooperation_probability", 0.8), "cooperation_probability"
        ),
        "strategic_behavior": strategic,
        "bounded_rationality": _probability(
            raw.get("bounded_rationality", 0.2), "bounded_rationality"
        ),
        "assumption_driven": True,
    }


class InstitutionalIRValidator:
    """Normalizes one product-wide grammar mapped to I=(X,E,R,A,P,W,T,C,Sigma)."""

    def normalize(
        self,
        document: dict[str, Any],
        *,
        institution_id: str | None = None,
        version: str | None = None,
    ) -> dict[str, Any]:
        if not isinstance(document, dict):
            raise InstitutionalIRError("Institutional IR must be an object")
        source = _json(document, "Institutional IR")
        normalized_id = _identifier(
            institution_id if institution_id is not None else source.get("institution_id"),
            "institution_id",
        )
        normalized_version = _identifier(
            version if version is not None else source.get("version"), "version"
        )
        institution_type = _identifier(source.get("institution_type"), "institution_type").upper()
        raw_objects = source.get("objects")
        if not isinstance(raw_objects, list) or not raw_objects:
            raise InstitutionalIRError("Institutional IR requires a non-empty objects array")
        objects: list[dict[str, Any]] = []
        ids: set[str] = set()
        for raw in raw_objects:
            if not isinstance(raw, dict):
                raise InstitutionalIRError("every Institutional IR object must be an object")
            object_id = _identifier(raw.get("object_id"), "object_id")
            if object_id in ids:
                raise InstitutionalIRError(f"duplicate Institutional IR object_id: {object_id}")
            ids.add(object_id)
            object_type = str(raw.get("object_type", "")).upper()
            if object_type not in OBJECT_TYPES:
                raise InstitutionalIRError(f"unsupported Institutional IR object_type: {object_type}")
            refs = []
            for reference in raw.get("references", []):
                if not isinstance(reference, dict):
                    raise InstitutionalIRError("object references must be objects")
                refs.append({
                    "relation": _identifier(reference.get("relation"), "reference relation").upper(),
                    "target_id": _identifier(reference.get("target_id"), "reference target_id"),
                })
            item = {
                "object_id": object_id,
                "object_type": object_type,
                "tuple_component": TUPLE_MAPPING[object_type],
                "name": _identifier(raw.get("name", object_id), "object name"),
                "attributes": _json(raw.get("attributes", {}), "object attributes"),
                "references": sorted(refs, key=lambda row: (row["relation"], row["target_id"])),
                "temporal_state": _normalize_temporal(raw.get("temporal_state")),
                "epistemic_state": _normalize_epistemic(
                    raw.get("epistemic_state"), object_type=object_type
                ),
            }
            if object_type == "ACTOR":
                item["behavior_model"] = _normalize_behavior(raw.get("behavior_model"))
            elif raw.get("behavior_model") is not None:
                raise InstitutionalIRError("behavior_model is only valid for ACTOR objects")
            objects.append(item)
        for item in objects:
            for reference in item["references"]:
                if reference["target_id"] not in ids:
                    raise InstitutionalIRError(
                        f"unresolved reference from {item['object_id']} to {reference['target_id']}"
                    )
        horizons = []
        seen_horizons: set[str] = set()
        for raw in source.get("horizons", []):
            if not isinstance(raw, dict):
                raise InstitutionalIRError("horizons must contain objects")
            horizon_id = _identifier(raw.get("horizon_id"), "horizon_id")
            if horizon_id in seen_horizons:
                raise InstitutionalIRError(f"duplicate horizon_id: {horizon_id}")
            seen_horizons.add(horizon_id)
            seconds = int(raw.get("duration_seconds", 0))
            if seconds <= 0:
                raise InstitutionalIRError("horizon duration_seconds must be positive")
            horizons.append({
                "horizon_id": horizon_id,
                "duration_seconds": seconds,
                "label": _identifier(raw.get("label", horizon_id), "horizon label"),
            })
        if not horizons:
            horizons = [
                {"horizon_id": "immediate", "duration_seconds": 10, "label": "10 seconds"},
                {"horizon_id": "operational", "duration_seconds": 3600, "label": "1 hour"},
                {"horizon_id": "strategic", "duration_seconds": 2_592_000, "label": "30 days"},
            ]
        horizons.sort(key=lambda row: (row["duration_seconds"], row["horizon_id"]))
        result = {
            "schema_version": "actionnet-institutional-ir.v1",
            "institution_id": normalized_id,
            "version": normalized_version,
            "institution_type": institution_type,
            "canonical_tuple": "I=(X,E,R,A,P,W,T,C,Sigma)",
            "objects": sorted(objects, key=lambda row: row["object_id"]),
            "horizons": horizons,
            "truth_layers": {
                "normative": list(source.get("truth_layers", {}).get("normative", [])),
                "operational": list(source.get("truth_layers", {}).get("operational", [])),
                "behavioral": list(source.get("truth_layers", {}).get("behavioral", [])),
            },
            "source_grounded": bool(source.get("source_grounded", False)),
            "authoritative": False,
            "binding_authority": False,
        }
        result["ir_sha256"] = sha256_json(result)
        return result

    def assess_actionability(self, document: dict[str, Any]) -> dict[str, Any]:
        ir = self.normalize(document)
        blockers = []
        for item in ir["objects"]:
            epistemic = item["epistemic_state"]
            if not epistemic["critical"]:
                continue
            if epistemic["status"] in NON_ACTIONABLE_EPISTEMIC:
                blockers.append({
                    "object_id": item["object_id"],
                    "status": epistemic["status"],
                    "reason": "critical institutional state is not action-ready",
                })
            elif epistemic["status"] in {"ESTIMATED", "PROBABILISTIC"} and epistemic["confidence"] < 0.5:
                blockers.append({
                    "object_id": item["object_id"],
                    "status": epistemic["status"],
                    "reason": "critical estimate is below the registered confidence floor",
                })
        return {
            "disposition": "ABSTAIN_ACQUIRE_EVIDENCE" if blockers else "ACTIONABLE_FOR_SIMULATION",
            "blockers": blockers,
            "ir_sha256": ir["ir_sha256"],
            "binding_authority": False,
        }


class HumanBehaviorEngine:
    """Produces deterministic assumption-driven scenarios, never predictions of people."""

    def generate(self, document: dict[str, Any], *, seed: int) -> dict[str, Any]:
        ir = InstitutionalIRValidator().normalize(document)
        rng = random.Random(int(seed))
        scenarios = []
        for actor in (item for item in ir["objects"] if item["object_type"] == "ACTOR"):
            model = actor["behavior_model"]
            trust_values = list(model["trust"].values())
            trust = sum(trust_values) / len(trust_values) if trust_values else 0.5
            effective_cooperation = model["cooperation_probability"]
            effective_cooperation *= 1 - 0.4 * model["fatigue"]
            effective_cooperation *= 0.75 + 0.25 * trust
            effective_cooperation = max(0.0, min(1.0, effective_cooperation))
            misexecution_probability = min(
                1.0, model["bounded_rationality"] * (0.5 + 0.5 * model["fatigue"])
            )
            draw = rng.random()
            if draw <= effective_cooperation:
                disposition = "COOPERATE"
            elif model["strategic_behavior"] in {"ADVERSARIAL", "OPPORTUNISTIC"}:
                disposition = "RESIST"
            else:
                disposition = "DELAY"
            scenarios.append({
                "actor_id": actor["object_id"],
                "disposition": disposition,
                "effective_cooperation_probability": round(effective_cooperation, 8),
                "misexecution_probability": round(misexecution_probability, 8),
                "sampled_misexecution": rng.random() < misexecution_probability,
                "assumptions_sha256": sha256_json(model),
            })
        record = {
            "schema_version": "actionnet-human-behavior-scenario.v1",
            "institution_ir_sha256": ir["ir_sha256"],
            "seed": int(seed),
            "scenarios": scenarios,
            "model_status": "ASSUMPTION_DRIVEN_SCENARIO_NOT_HUMAN_GROUND_TRUTH",
            "authoritative": False,
            "binding_authority": False,
        }
        record["scenario_sha256"] = sha256_json(record)
        return deepcopy(record)