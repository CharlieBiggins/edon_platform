#!/usr/bin/env python3
"""Deterministic, auditable expert routing for ActionNet candidates."""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent
DOMAIN_REGISTRY = json.loads((ROOT / "registry" / "domains.json").read_text(encoding="utf-8"))
REQUIREMENTS = json.loads((ROOT / "registry" / "expert_requirements.json").read_text(encoding="utf-8"))
DOMAIN_BY_ID = {item["domain_id"]: item for item in DOMAIN_REGISTRY["domains"]}


def review_policy(risk_tier: str) -> dict[str, Any]:
    return dict(REQUIREMENTS["review_policy"][risk_tier])


def build_review_queue(pairs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Create one review item per structured pair, not one item per renderer/task."""
    queue: list[dict[str, Any]] = []
    for pair in pairs:
        base = pair["base"]
        domain = DOMAIN_BY_ID[base["domain"]]
        policy = review_policy(domain["risk_tier"])
        queue.append({
            "review_item_id": "review-" + pair["counterfactual_pair_id"].split("-", 1)[-1],
            "candidate_pair_id": pair["counterfactual_pair_id"],
            "split": pair["split"],
            "domain_id": domain["domain_id"],
            "workflow_name": base["workflow_name"],
            "jurisdiction": base["jurisdiction"],
            "risk_tier": domain["risk_tier"],
            "mechanism": pair["intervention_family"],
            "required_specialties": domain["expert_specialties"],
            "independent_reviews_required": policy["independent_reviews"],
            "adjudicator_required": policy.get("adjudicator_required", False),
            "safety_review_required": policy.get("safety_review_required", False),
            "source_grounded": False,
            "source_permission_status": "NOT_APPLICABLE_SYNTHETIC",
            "privacy_review_status": "PENDING",
            "review_status": "UNASSIGNED",
            "training_eligible": False,
            "binding_authority": False,
        })
    return queue


def eligibility_reasons(profile: dict[str, Any], item: dict[str, Any], *, as_of: date | None = None) -> list[str]:
    as_of = as_of or date.today()
    reasons: list[str] = []
    if profile.get("profile_status") != "VERIFIED":
        reasons.append("PROFILE_NOT_VERIFIED")
    if float(profile.get("calibration_score", 0.0)) < float(REQUIREMENTS["eligibility"]["minimum_calibration_score"]):
        reasons.append("CALIBRATION_BELOW_MINIMUM")
    expires = profile.get("credential_expires_on")
    if not expires or date.fromisoformat(expires) < as_of:
        reasons.append("CREDENTIAL_EXPIRED_OR_MISSING")
    if item["domain_id"] not in set(profile.get("verified_domains", [])):
        reasons.append("DOMAIN_NOT_VERIFIED")
    if not set(item["required_specialties"]) & set(profile.get("verified_specialties", [])):
        reasons.append("SPECIALTY_MISMATCH")
    if item["jurisdiction"] not in set(profile.get("verified_jurisdictions", [])):
        reasons.append("JURISDICTION_MISMATCH")
    if not profile.get("conflict_attestation_current", False):
        reasons.append("CONFLICT_ATTESTATION_MISSING")
    if item.get("candidate_pair_id") in set(profile.get("authored_candidate_ids", [])):
        reasons.append("SELF_REVIEW_PROHIBITED")
    if item.get("tenant_id") and item["tenant_id"] not in set(profile.get("permitted_tenants", [])):
        reasons.append("TENANT_PERMISSION_MISSING")
    return reasons


def routing_score(profile: dict[str, Any], item: dict[str, Any]) -> float:
    specialty_matches = len(set(item["required_specialties"]) & set(profile.get("verified_specialties", [])))
    return round(
        40.0
        + min(30.0, specialty_matches * 15.0)
        + 15.0
        + float(profile.get("calibration_score", 0.0)) * 10.0
        + min(5.0, float(profile.get("completed_reviews", 0)) / 20.0),
        4,
    )


def route_item(item: dict[str, Any], profiles: list[dict[str, Any]], *, as_of: date | None = None) -> dict[str, Any]:
    eligible = []
    rejected = []
    for profile in profiles:
        reasons = eligibility_reasons(profile, item, as_of=as_of)
        if reasons:
            rejected.append({"expert_id": profile.get("expert_id"), "reasons": reasons})
        else:
            eligible.append({
                "expert_id": profile["expert_id"],
                "affiliation_id": profile.get("affiliation_id", profile["expert_id"]),
                "score": routing_score(profile, item),
            })
    eligible.sort(key=lambda row: (-row["score"], row["expert_id"]))
    needed = int(item["independent_reviews_required"])
    assignments = []
    used_affiliations = set()
    for candidate in eligible:
        if candidate["affiliation_id"] in used_affiliations:
            continue
        assignments.append(candidate)
        used_affiliations.add(candidate["affiliation_id"])
        if len(assignments) == needed:
            break
    return {
        **item,
        "assigned_experts": assignments,
        "routing_status": "ASSIGNED" if len(assignments) == needed else "INSUFFICIENT_QUALIFIED_EXPERTS",
        "eligible_expert_count": len(eligible),
        "independent_affiliation_count": len({row["affiliation_id"] for row in eligible}),
        "rejected_experts": rejected,
        "routing_policy_version": REQUIREMENTS["schema_version"],
    }


def route_queue(items: list[dict[str, Any]], profiles: list[dict[str, Any]], *, as_of: date | None = None) -> list[dict[str, Any]]:
    return [route_item(item, profiles, as_of=as_of) for item in items]