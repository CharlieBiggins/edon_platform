#!/usr/bin/env python3
"""Pure functions for evaluating ActionNet training eligibility."""

from __future__ import annotations

from copy import deepcopy
from typing import Any


PASS_OR_NA = {"PASS", "NOT_APPLICABLE"}


def evaluate_training_gate(gate: dict[str, str]) -> dict[str, Any]:
    requirements = {
        "tenant_permission": PASS_OR_NA,
        "source_permission": PASS_OR_NA,
        "privacy_review": PASS_OR_NA,
        "deidentification": PASS_OR_NA,
        "expert_review": {"PASS"},
        "adjudication": {"PASS", "NOT_REQUIRED"},
        "duplicate_check": {"PASS"},
        "protected_case_excluded": {"PASS"},
        "dataset_freeze": {"PASS"},
        "release_approval": {"PASS"},
    }
    failed = [name for name, accepted in requirements.items() if gate.get(name) not in accepted]
    return {"eligible": not failed, "failed_gates": failed}


def attach_training_gate(candidate: dict[str, Any], gate: dict[str, str]) -> dict[str, Any]:
    result = deepcopy(candidate)
    evaluation = evaluate_training_gate(gate)
    result["training_gate"] = {**gate, **evaluation}
    result["training_eligible"] = evaluation["eligible"]
    return result