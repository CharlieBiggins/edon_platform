"""Contradiction, leakage, reachability, pivotality, and safety checks."""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from edon.common.hashing import canonical_json, sha256_json
from edon.runtime import validate_approved_mechanism


FORBIDDEN_PUBLIC_KEYS = {"target", "label", "labels", "expected", "oracle", "completion"}
REQUIRED_TASKS = {"CERTIFICATE", "TRANSITION", "QUEUE_TRACE", "PAIR_CONTRAST"}


def _forbidden_paths(value: Any, path: str = "$") -> list[str]:
    found: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            child_path = f"{path}.{key}"
            if key.casefold() in FORBIDDEN_PUBLIC_KEYS:
                found.append(child_path)
            found.extend(_forbidden_paths(child, child_path))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            found.extend(_forbidden_paths(child, f"{path}[{index}]"))
    return found


def _oracle_decision(label: dict[str, Any]) -> str | None:
    if isinstance(label.get("decision"), str):
        return label["decision"]
    certificate = label.get("certificate")
    if isinstance(certificate, dict) and isinstance(certificate.get("decision"), str):
        return certificate["decision"]
    return None


def qualify_actionnet(mechanism: dict[str, Any], bundle: dict[str, Any]) -> dict[str, Any]:
    public_cases = bundle.get("public", {}).get("cases", [])
    labels = bundle.get("protected", {}).get("labels", {})
    case_ids = [case.get("case_id") for case in public_cases]
    leakage_paths = _forbidden_paths(bundle.get("public", {}))
    tasks = {case.get("task_type") for case in public_cases}

    input_targets: dict[str, set[str]] = defaultdict(set)
    unsafe_case_ids: list[str] = []
    unreachable_case_ids: list[str] = []
    pair_paths: set[str] = set()
    for case in public_cases:
        case_id = case.get("case_id")
        label = labels.get(case_id)
        if not isinstance(label, dict):
            unreachable_case_ids.append(str(case_id))
            continue
        input_hash = sha256_json({
            "observation": case.get("observation"),
            "query": case.get("query"),
            "task_type": case.get("task_type"),
        })
        input_targets[input_hash].add(canonical_json(label))
        scenario = case.get("observation", {}).get("scenario_class")
        decision = _oracle_decision(label)
        if scenario in {"FAILURE", "EDGE"} and decision == "ALLOW":
            unsafe_case_ids.append(str(case_id))
        if case.get("task_type") == "PAIR_CONTRAST" and label.get("decision_changed") is True:
            pair_paths.add(str(label.get("causal_path")))

    expected_paths = {
        f"{fact['subject']}.{fact['predicate']}" for fact in mechanism.get("facts", [])
    }
    conflicting_inputs = sorted(
        digest for digest, targets in input_targets.items() if len(targets) > 1
    )
    mechanism_checks = validate_approved_mechanism(mechanism)
    checks = {
        "mechanism_runtime_valid": all(mechanism_checks.values()),
        "public_cases_present": bool(public_cases),
        "oracle_labels_present": bool(labels),
        "case_ids_unique": len(case_ids) == len(set(case_ids)),
        "case_label_counts_match": len(public_cases) == len(labels),
        "no_public_label_leakage": not leakage_paths,
        "no_conflicting_targets_for_identical_inputs": not conflicting_inputs,
        "all_cases_reachable": not unreachable_case_ids,
        "all_required_tasks_present": REQUIRED_TASKS <= tasks,
        "all_constraints_have_pivotal_pairs": expected_paths <= pair_paths,
        "zero_unsafe_failure_allows": not unsafe_case_ids,
        "public_and_protected_hashes_distinct": (
            bundle.get("manifest", {}).get("public_sha256")
            != bundle.get("manifest", {}).get("protected_sha256")
        ),
        "labels_separated": bundle.get("manifest", {}).get("labels_separated") is True,
    }
    return {
        "schema_version": "edon-actionnet-qualification.v1",
        "mechanism_id": mechanism.get("mechanism_id"),
        "checks": checks,
        "checks_passed": sum(checks.values()),
        "check_count": len(checks),
        "passed": all(checks.values()),
        "status": "ACTIONNET_QUALIFIED" if all(checks.values()) else "ACTIONNET_REJECTED",
        "diagnostics": {
            "leakage_paths": leakage_paths,
            "conflicting_input_hashes": conflicting_inputs,
            "unreachable_case_ids": unreachable_case_ids,
            "unsafe_case_ids": unsafe_case_ids,
            "missing_pivotal_paths": sorted(expected_paths - pair_paths),
            "task_types": sorted(str(task) for task in tasks),
        },
        "bundle_public_sha256": bundle.get("manifest", {}).get("public_sha256"),
        "binding_authority": False,
    }