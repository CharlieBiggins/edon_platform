#!/usr/bin/env python3
"""Classify governed application feedback before ActionNet construction."""

from __future__ import annotations

from typing import Any


HIGH_VALUE_REASON_CODES = {
    "policy_gap",
    "unsafe_allow",
    "unsafe_deny",
    "missed_escalation",
    "wrong_authority",
    "missing_evidence_requirement",
    "bad_state_transition",
    "workflow_mismatch",
    "jurisdiction_mismatch",
    "time_window_mismatch",
    "resource_constraint_missed",
    "conflict_not_detected",
}


def classify_feedback_event(event: dict[str, Any]) -> dict[str, Any]:
    if event.get("protected_case"):
        return {"classification": "EXCLUDED", "reason": "PROTECTED_CASE", "training_eligible": False}
    if event.get("learning_mode") == "disabled":
        return {"classification": "OPERATIONAL_EVIDENCE_ONLY", "reason": "LEARNING_DISABLED", "training_eligible": False}
    if not event.get("human_correction"):
        return {"classification": "OPERATIONAL_EVIDENCE_ONLY", "reason": "NO_HUMAN_CORRECTION", "training_eligible": False}
    matched = sorted(set(event.get("reason_codes", [])) & HIGH_VALUE_REASON_CODES)
    if not matched:
        return {"classification": "OPERATIONAL_EVIDENCE_ONLY", "reason": "NO_QUALIFYING_REASON_CODE", "training_eligible": False}
    return {
        "classification": "ACTIONNET_CANDIDATE",
        "reason": "GOVERNED_CORRECTIVE_SIGNAL",
        "matched_reason_codes": matched,
        "next_status": "PENDING_PRIVACY_AND_SOURCE_REVIEW",
        "training_eligible": False,
    }