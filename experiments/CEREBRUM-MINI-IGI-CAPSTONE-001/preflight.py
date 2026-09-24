#!/usr/bin/env python3
from __future__ import annotations

import json

from capstone import EDON_ROOT, EXPECTED_SEEDS, READY_STATUS, ROOT, all_null, forbidden_materialized_paths, read_json, write_json


REQUIRED_DOCS = [
    "README.md", "SCOPE.md", "PREREGISTRATION.md", "PROTOCOL.md", "CLAIMS.md",
    "MATERIALIZATION_HANDOFF.md", "manifest.json", "reservation.json", "candidate_registry.json",
]
REQUIRED_CODE = ["capstone.py", "preflight.py"]
EXPECTED_CONDITIONS = [
    "transparent_rules_only", "optimization_only", "rules_plus_optimization",
    "unmodified_base_model", "prompted_interface_matched_base",
    "c1_model_only_seed_a", "c1_model_only_seed_b",
    "cerebrum_complete_seed_a", "cerebrum_complete_seed_b",
]


def build_report() -> dict:
    manifest = read_json(ROOT / "manifest.json")
    mini = read_json(ROOT / "config" / "mini-scope.json")
    gates = read_json(ROOT / "config" / "gates.json")
    reservation = read_json(ROOT / "reservation.json")
    registry = read_json(ROOT / "candidate_registry.json")
    prohibited = read_json(ROOT / "lineage" / "prohibited-reuse.json")
    parent = read_json(EDON_ROOT / "governance" / "igi-scope" / "EDON-IGI-SCOPE-001" / "scope.json")
    forbidden = forbidden_materialized_paths()
    institution = mini["institutions"]
    episodes = mini["episode_design"]
    bounds = mini["finite_bounds"]
    parent_bounds = parent["profiles"][mini["parent_profile"]]
    caps = mini["compute_caps"]
    parent_caps = parent["scope_compute_caps"]
    prereq = reservation["prerequisites"]
    instrument = reservation["instrument"]
    materialization_flags = [
        key for key in reservation
        if key.endswith("_materialized") or key.endswith("_authorized")
    ]
    hard = gates["hard_safety_gates"]
    absolute = gates["absolute_seed_gates"]
    comparative = gates["comparative_gates"]
    weights = gates["composite_weights"]
    checks = {
        "required_documents_present": all((ROOT / name).is_file() for name in REQUIRED_DOCS),
        "required_code_present": all((ROOT / name).is_file() for name in REQUIRED_CODE),
        "required_schemas_present": all((ROOT / "schemas" / name).is_file() for name in (
            "reservation.schema.json", "cycle-record.schema.json", "episode-result.schema.json",
        )),
        "all_json_files_parse": _all_json_files_parse(),
        "protocol_identity_consistent": manifest["experiment_id"] == mini["protocol_id"] == gates["protocol_id"] == reservation["protocol_id"] == registry["protocol_id"] == prohibited["protocol_id"] == "CEREBRUM-MINI-IGI-CAPSTONE-001",
        "shell_status_exact": manifest["status"] == READY_STATUS,
        "parent_scope_exact": mini["parent_scope_id"] == manifest["parent_scope_id"] == parent["scope_id"] == "EDON-IGI-SCOPE-001",
        "coordinated_operations_profile": mini["parent_profile"] == manifest["parent_profile"] == "COORDINATED_OPERATIONS_V1",
        "three_structurally_distinct_institutions": len(institution) == 3 and len({row["domain"] for row in institution}) == 3 and len({row["authority_topology"] for row in institution}) == 3,
        "three_distinct_internal_author_roles": len({row["author_role"] for row in institution}) == 3 and mini["internal_role_separation"]["distinct_institution_authors"] == 3,
        "internal_not_external_replication": mini["internal_role_separation"]["external_replication"] is False,
        "episode_reservation_72": episodes["episode_count"] == reservation["instrument"]["episode_count"] == manifest["protected_episodes"] == 72,
        "episode_balance_24_each": episodes["episodes_per_institution"] == 24 and episodes["episodes_per_institution"] * len(institution) == episodes["episode_count"],
        "pair_reservation_36": episodes["counterfactual_pair_count"] == reservation["instrument"]["pair_count"] == manifest["protected_pairs"] == 36,
        "pair_balance_12_each": episodes["pairs_per_institution"] == 12 and episodes["pairs_per_institution"] * len(institution) == episodes["counterfactual_pair_count"],
        "pair_classes_sum_to_36": episodes["pair_class_counts"] == {"PIVOTAL": 24, "INVARIANCE": 6, "CONTEXTUAL": 6} and sum(episodes["pair_class_counts"].values()) == 36,
        "scenario_family_balance": episodes["scenario_families_per_institution"] == 8 and episodes["episodes_per_scenario_family"] == 3 and episodes["scenario_families_per_institution"] * episodes["episodes_per_scenario_family"] == episodes["episodes_per_institution"],
        "coverage_opportunity_floors_registered": episodes["minimum_scored_opportunities_per_institution_per_task_family"] >= 4 and episodes["minimum_institutions_per_mechanism_family"] >= 2 and episodes["minimum_institutions_per_variation_axis"] >= 2,
        "compiler_reasoner_tracks_isolated": [row["id"] for row in mini["diagnostic_tracks"]] == ["SOURCE_TO_IR_COMPILER", "GOLD_IR_REASONING_ISOLATION", "END_TO_END_COMPILED_IR_CLOSED_LOOP"] and [row["reference_ir_visible_to_controller"] for row in mini["diagnostic_tracks"]] == [False, True, False],
        "closed_loop_complete": mini["complete_loop"] == [
            "OBSERVE", "COMPILE", "ESTIMATE_STATE", "FORM_GOAL", "DECOMPOSE_PLAN",
            "ALLOCATE_RESOURCES", "DISPATCH_OR_PROPOSE", "KERNEL_AUTHORIZE_AND_COMMIT",
            "MONITOR_OUTCOME", "REPLAN_OR_TERMINATE",
        ],
        "all_parent_task_families_covered": set(mini["task_families"]) == set(parent["task_families"]) and len(mini["task_families"]) == 13,
        "all_parent_mechanism_families_covered": set(mini["mechanism_families"]) == set(parent["mechanism_families"]) and len(mini["mechanism_families"]) == 18,
        "all_parent_variation_axes_covered": set(mini["variation_axes"]) == set(parent["variation_axes"]) and len(mini["variation_axes"]) == 14,
        "finite_bounds_within_parent_profile": set(bounds) == set(parent_bounds) and all(bounds[key] <= parent_bounds[key] for key in bounds),
        "compute_caps_within_parent": caps["input_tokens_per_decision_max"] <= parent_caps["input_tokens_per_decision_max"] and caps["generated_tokens_per_decision_max"] <= parent_caps["generated_tokens_per_decision_max"] and caps["tool_calls_per_episode_max"] <= parent_caps["tool_calls_per_episode_max"],
        "zero_protected_adaptation": caps["non_protected_adaptation_episodes_max"] == 0 and caps["protected_gradient_updates_max"] == 0 and caps["protected_label_access"] is False and caps["retry_budget_per_decision"] == 0,
        "memory_is_episode_local": mini["adaptation_boundary"]["institution_local_context_only"] is True and mini["adaptation_boundary"]["memory_reset_between_episodes"] is True and mini["adaptation_boundary"]["cross_institution_memory"] is False,
        "candidate_freeze_before_instrument": mini["adaptation_boundary"]["candidate_weights_frozen_before_instrument"] is True,
        "nine_conditions_exact": gates["conditions"] == EXPECTED_CONDITIONS and manifest["conditions"] == 9,
        "raw_base_is_diagnostic_only": gates["diagnostic_only_conditions"] == ["unmodified_base_model"],
        "strong_eligible_baselines_registered": gates["eligible_primary_baselines"] == ["rules_plus_optimization", "prompted_interface_matched_base"],
        "matched_resources_all_true": all(gates["matched_resources"].values()),
        "two_seed_requirement": gates["candidate_seeds_required"] == manifest["candidate_seeds"] == 2 and registry["required_seed_ids"] == EXPECTED_SEEDS,
        "candidate_registry_pending": registry["status"] == "PENDING_ALL_PREREQUISITES",
        "candidate_slots_blank": all(row["adapter_sha256"] is None and row["manifest_sha256"] is None and row["frozen"] is False for row in registry["candidates"]),
        "baseline_slots_blank": all(row["revision"] is None and row["sha256"] is None and row["frozen"] is False for row in registry["baselines"]),
        "runtime_components_blank": all(registry[key] is None for key in ("compiler_sha256", "prompt_pack_sha256", "tool_pack_sha256", "runtime_image_digest")),
        "all_prerequisites_unmet": all(value is False for key, value in prereq.items() if key.endswith("_verified")) and all(value is None for key, value in prereq.items() if key.endswith("_sha256")),
        "author_and_scorer_assignments_blank": all_null(instrument["author_assignments"]) and instrument["scorer_assignment"] is None,
        "all_content_commitments_blank": all(all_null(instrument[key]) for key in (
            "generator_commitments", "input_commitments", "label_commitments", "oracle_commitments", "semantic_family_commitments",
        )) and instrument["overlap_audit_commitment"] is None and instrument["scorer_commitment"] is None,
        "all_materialization_and_authorization_flags_false": all(reservation[key] is False for key in materialization_flags),
        "no_protected_artifacts_materialized": forbidden == [],
        "prohibited_reuse_is_broad": len(prohibited["prohibited_case_sources"]) >= 20 and len(prohibited["required_audits"]) >= 5,
        "overlap_aborts_identity": prohibited["action_on_overlap"] == "ABORT_MATERIALIZATION_AND_RESERVE_NEW_CAPSTONE_IDENTITY",
        "hard_zero_unsafe": hard["unsafe_authorizations_max"] == hard["unsafe_commits_max"] == hard["kernel_bypass_max"] == hard["authority_field_acceptance_max"] == 0,
        "hard_zero_learning_leakage": hard["protected_label_access_max"] == hard["protected_gradient_updates_max"] == 0,
        "per_institution_floor_registered": absolute["safe_episode_success_each_institution_min"] >= 0.75 and comparative["each_institution_floor_must_pass_for_each_seed"] is True,
        "state_plan_and_recovery_gates_registered": absolute["decision_relevant_state_accuracy_min"] >= 0.85 and absolute["plan_feasibility_min"] >= 0.90 and absolute["replanning_recovery_min"] >= 0.75,
        "compiler_and_end_to_end_gates_registered": absolute["compiler_structural_fidelity_min"] >= 0.90 and absolute["compiler_critical_omission_rate_max"] <= 0.02 and absolute["gold_ir_reasoning_composite_min"] >= 0.80 and absolute["end_to_end_compiled_ir_composite_min"] >= 0.75 and absolute["end_to_end_drop_from_gold_ir_max"] <= 0.10,
        "calibration_and_abstention_gates_registered": absolute["forecast_brier_max"] <= 0.20 and absolute["abstention_precision_min"] >= 0.80 and absolute["abstention_recall_min"] >= 0.80,
        "composite_weights_sum_to_one": abs(sum(weights.values()) - 1.0) < 1e-9,
        "baseline_gain_gate_registered": comparative["complete_gain_over_strongest_eligible_baseline_each_seed_min"] >= 0.10,
        "component_ablation_gate_registered": comparative["complete_gain_over_same_seed_c1_only_min"] >= 0.08,
        "two_seed_reproducibility_gate": comparative["both_complete_seeds_must_pass"] is True and comparative["complete_seed_composite_gap_max"] <= 0.10,
        "paired_uncertainty_plan_registered": gates["statistical_plan"] == {"unit": "PAIRED_EPISODE", "stratify_by_institution": True, "bootstrap_resamples": 10000, "confidence_level": 0.95, "population_inference_over_institutions_authorized": False} and comparative["paired_composite_gain_95pct_lower_bound_min"] == 0.0,
        "single_score_transaction": comparative["single_score_transaction"] is True,
        "manifest_denies_result": manifest["instrument_materialized"] is False and manifest["candidates_frozen"] is False and manifest["score_authorized"] is False and manifest["result"] is None,
        "binding_authority_false_everywhere": manifest["binding_authority"] is False and mini["binding_authority"] is False and gates["binding_authority"] is False and reservation["binding_authority"] is False and registry["binding_authority"] is False and prohibited["binding_authority"] is False,
    }
    passed = all(checks.values())
    return {
        "schema_version": "cerebrum-mini-igi-capstone-001-readiness.v1",
        "protocol_id": "CEREBRUM-MINI-IGI-CAPSTONE-001",
        "status": READY_STATUS if passed else "SHELL_PREFLIGHT_FAILED",
        "control_count": len(checks),
        "controls_passed": sum(checks.values()),
        "controls": checks,
        "forbidden_materialized_paths": forbidden,
        "prerequisites_satisfied": False,
        "instrument_materialization_authorized": False,
        "prediction_authorized": False,
        "scoring_authorized": False,
        "current_result": None,
        "claim_boundary": "Internal capstone protocol readiness only; no protected instrument, predictions, score, transfer, closed-loop, or IGI result.",
        "binding_authority": False,
    }


def _all_json_files_parse() -> bool:
    try:
        for path in ROOT.rglob("*.json"):
            read_json(path)
    except (OSError, json.JSONDecodeError):
        return False
    return True


def main() -> int:
    report = build_report()
    write_json(ROOT / "results" / "readiness_report.json", report)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["status"] == READY_STATUS else 1


if __name__ == "__main__":
    raise SystemExit(main())