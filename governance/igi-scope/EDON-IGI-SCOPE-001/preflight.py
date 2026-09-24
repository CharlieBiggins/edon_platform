#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent
EDON = ROOT.parents[2]


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def build_report() -> dict:
    scope = read_json(ROOT / "scope.json")
    coverage = read_json(ROOT / "coverage-matrix.json")
    manifest = read_json(ROOT / "scope-manifest.json")
    inventory = read_json(ROOT / "inventory.json")
    registry = read_json(ROOT.parent / "registry.json")
    transfer_root = EDON / "experiments" / "CEREBRUM-TRANSFER-008"
    required_files = {
        "README.md", "SCOPE.md", "EVALUATION_PROFILES.md", "CLAIMS.md",
        "VERSIONING.md", "scope.json", "coverage-matrix.json",
        "scope.schema.json", "scope-manifest.json", "inventory.json",
        "preflight.py", "tests/test_scope.py",
    }
    inventory_files = inventory["files"]
    profile_keys = [
        "typed_state_paths_max", "roles_max", "agents_max", "resource_types_max",
        "simultaneous_goals_max", "plan_steps_max", "queued_events_max",
        "horizon_events_max", "mechanism_instances_max", "authority_depth_max",
        "federation_scopes_max", "tool_calls_max", "observation_delay_ticks_max",
        "serialized_observation_bytes_max",
    ]
    profile_values_valid = all(
        all(isinstance(profile.get(key), int) and profile[key] > 0 for key in profile_keys)
        for profile in scope["profiles"].values()
    )
    ordered = list(scope["profiles"].values())
    profiles_nested = all(
        all(ordered[index][key] <= ordered[index + 1][key] for key in profile_keys)
        for index in range(len(ordered) - 1)
    )
    inventory_matches = all(
        (ROOT / path).is_file() and sha256(ROOT / path) == digest
        for path, digest in inventory_files.items()
    )
    transfer = scope["transfer008_relation"]
    checks = {
        "required_files_present": required_files.issubset({
            path.relative_to(ROOT).as_posix() for path in ROOT.rglob("*") if path.is_file()
        }),
        "scope_identity": scope["scope_id"] == manifest["scope_id"] == "EDON-IGI-SCOPE-001",
        "version_frozen": scope["version"] == manifest["version"] == "1.0.0" and scope["frozen"] == "2026-08-25",
        "definition_not_result": scope["status"] == "FROZEN_DEFINITION_NO_IGI_RESULT" == manifest["status"],
        "registry_entry_present": any(row["scope_id"] == scope["scope_id"] for row in registry["scopes"]),
        "finite_discrete_typed_environment": scope["formal_environment"]["finite"] is True and scope["formal_environment"]["discrete_event"] is True and scope["formal_environment"]["typed_state_required"] is True,
        "proposal_only_control_surface": scope["formal_environment"]["learned_control_surface"] == "NON_BINDING_PROPOSALS_ONLY",
        "kernel_binding_authority": scope["formal_environment"]["binding_transition_authority"] == "DETERMINISTIC_INSTITUTION_LOCAL_KERNEL",
        "mechanism_breadth": len(scope["mechanism_families"]) >= 18 and len(set(scope["mechanism_families"])) == len(scope["mechanism_families"]),
        "task_breadth": len(scope["task_families"]) >= 13 and len(set(scope["task_families"])) == len(scope["task_families"]),
        "variation_breadth": len(scope["variation_axes"]) >= 14 and len(set(scope["variation_axes"])) == len(scope["variation_axes"]),
        "three_profiles": list(scope["profiles"]) == ["EVENTNET_CORE_V1", "COORDINATED_OPERATIONS_V1", "FEDERATED_INSTITUTION_V1"],
        "profile_values_positive": profile_values_valid,
        "profiles_nested": profiles_nested,
        "finite_compute_caps": all(isinstance(value, int) and value >= 0 for key, value in scope["scope_compute_caps"].items() if key.endswith("_max")),
        "zero_protected_gradient_updates": scope["scope_compute_caps"]["protected_gradient_updates_max"] == 0,
        "protected_labels_forbidden": scope["scope_compute_caps"]["protected_label_access"] is False,
        "matched_baseline_budget": scope["scope_compute_caps"]["matched_baseline_information_tools_and_compute"] is True,
        "safety_invariants_registered": len(scope["safety_invariants"]) >= 14,
        "zero_unsafe_invariant": "ZERO_UNSAFE_AUTHORIZATIONS" in scope["safety_invariants"],
        "authority_invariants": all(name in scope["safety_invariants"] for name in ("BINDING_AUTHORITY_FALSE", "ZERO_AUTHORITY_FIELD_ACCEPTANCE", "KERNEL_ONLY_COMMIT")),
        "transfer_requirements_registered": len(scope["independent_transfer_requirements"]) >= 8,
        "independent_generator_required_for_strongest_tier": "INDEPENDENT_GENERATOR_OR_REAL_INSTITUTION_FOR_STRONGEST_TIER" in scope["independent_transfer_requirements"],
        "exclusions_registered": len(scope["excluded_environment_classes"]) >= 12,
        "universal_environment_claim_excluded": "CLAIMS_OVER_ALL_COMPUTABLE_ENVIRONMENTS" in scope["excluded_environment_classes"],
        "evidence_tiers_ordered": scope["evidence_tiers"][0].startswith("T0_") and scope["evidence_tiers"][-1].startswith("T6_"),
        "transfer008_is_narrow_slice": transfer["role"] == "FIRST_NARROW_INDEPENDENT_EVENTNET_EVIDENCE_SLICE" and transfer["profile"] == "EVENTNET_CORE_V1",
        "transfer008_task_count_four": transfer["tasks"] == ["CERTIFICATE", "TRANSITION", "QUEUE_TRACE", "PAIR_CONTRAST"],
        "transfer008_cannot_establish_full_scope": "FULL_SCOPE001_COVERAGE" in transfer["cannot_establish"] and "UNIVERSAL_IGI" in transfer["cannot_establish"],
        "transfer008_manifest_anchor": sha256(transfer_root / "manifest.json") == transfer["manifest_sha256"],
        "transfer008_reservation_anchor": sha256(transfer_root / "reservation.json") == transfer["reservation_sha256"],
        "transfer008_gate_anchor": sha256(transfer_root / "config" / "transfer-gates.json") == transfer["gates_sha256"],
        "scope_artifact_hash": sha256(ROOT / "scope.json") == manifest["artifact"]["sha256"],
        "inventory_complete": required_files - {"scope-manifest.json", "inventory.json"} <= set(inventory_files),
        "inventory_hashes_match": inventory_matches,
        "coverage_scope_identity": coverage["scope_id"] == scope["scope_id"],
        "coverage_not_established": coverage["scope_generality_established"] is False and coverage["universal_igi_established"] is False,
        "current_disposition_all_unproven": all(value is False for key, value in scope["current_disposition"].items() if key != "scope_defined"),
        "scope_defined_only": scope["current_disposition"]["scope_defined"] is True,
        "universal_claim_blocked": scope["universal_claim_authorized"] is False and manifest["universal_claim_authorized"] is False,
        "external_and_production_blocked": scope["external_pilot_authorized"] is False and scope["production_authorized"] is False,
        "binding_authority_false": scope["binding_authority"] is False and coverage["binding_authority"] is False and manifest["binding_authority"] is False,
    }
    passed = all(checks.values())
    return {
        "schema_version": "edon-igi-scope-readiness.v1",
        "scope_id": scope["scope_id"],
        "control_count": len(checks),
        "controls_passed": sum(checks.values()),
        "controls": checks,
        "status": "FROZEN_SCOPE_DEFINITION_VALID_NO_IGI_RESULT" if passed else "SCOPE_PREFLIGHT_FAILED",
        "scope_generality_established": False,
        "universal_igi_established": False,
        "external_pilot_authorized": False,
        "production_authorized": False,
        "binding_authority": False,
        "claim_boundary": "Frozen bounded environment definition only; no transfer, generality, real-institution, universal IGI, or production result.",
    }


def main() -> int:
    report = build_report()
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["status"].startswith("FROZEN_SCOPE_DEFINITION_VALID") else 1


if __name__ == "__main__":
    raise SystemExit(main())