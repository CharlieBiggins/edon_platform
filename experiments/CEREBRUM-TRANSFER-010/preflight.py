#!/usr/bin/env python3
from __future__ import annotations

import json

from transfer010 import (
    BASE_REVISION,
    EXPECTED_SEEDS,
    ROOT,
    forbidden_materialized_paths,
    read_json,
    sha256_path,
    valid_sha256,
    write_json,
)


REQUIRED_DOCS = [
    "README.md",
    "PREREGISTRATION.md",
    "PROTOCOL.md",
    "CLAIMS.md",
    "CUSTODY.md",
    "MATERIALIZATION_HANDOFF.md",
    "manifest.json",
    "reservation.json",
    "candidate_registry.json",
    "baseline_registry.json",
]
REQUIRED_CODE = [
    "transfer010.py",
    "preflight.py",
    "register_candidates.py",
    "register_baselines.py",
    "authorize_materialization.py",
]
REQUIRED_CONFIG = [
    "config/transfer-gates.json",
    "config/baseline-contract.json",
    "config/authorship-custody-contract.json",
    "lineage/prohibited-predecessors.json",
]
REQUIRED_SCHEMAS = [
    "schemas/candidate-registry.schema.json",
    "schemas/baseline-registry.schema.json",
    "schemas/reservation.schema.json",
    "schemas/protected-input.schema.json",
    "schemas/protected-prediction.schema.json",
    "schemas/custody-commitments.schema.json",
]
COMMITMENTS = [
    "generator_seed_commitment",
    "generator_source_commitment",
    "oracle_source_commitment",
    "governance_form_commitment",
    "renderer_source_commitment",
    "input_commitment",
    "label_commitment",
    "overlap_audit_commitment",
    "authorship_attestation_commitment",
    "power_analysis_commitment",
]


def build_report() -> dict:
    manifest = read_json(ROOT / "manifest.json")
    gates = read_json(ROOT / "config" / "transfer-gates.json")
    reservation = read_json(ROOT / "reservation.json")
    candidates = read_json(ROOT / "candidate_registry.json")
    baseline_contract = read_json(ROOT / "config" / "baseline-contract.json")
    baseline_registry = read_json(ROOT / "baseline_registry.json")
    authorship = read_json(ROOT / "config" / "authorship-custody-contract.json")
    prohibited = read_json(ROOT / "lineage" / "prohibited-predecessors.json")
    forbidden = forbidden_materialized_paths()
    instrument = reservation["instrument"]
    baseline_names = [row["condition"] for row in baseline_contract["conditions"]]
    registry_names = [row["condition"] for row in baseline_registry["conditions"]]
    eligible = baseline_contract["primary_comparator"]["eligible_conditions"]
    checks = {
        "required_documents_present": all((ROOT / name).is_file() for name in REQUIRED_DOCS),
        "required_code_present": all((ROOT / name).is_file() for name in REQUIRED_CODE),
        "required_config_present": all((ROOT / name).is_file() for name in REQUIRED_CONFIG),
        "required_schemas_present": all((ROOT / name).is_file() for name in REQUIRED_SCHEMAS),
        "protocol_identity": manifest["experiment_id"] == "CEREBRUM-TRANSFER-010" == gates["protocol_id"] == reservation["protocol_id"],
        "status_reserved_and_blocked": manifest["status"] == "RESERVED_BLOCKED_PENDING_DEV010_TWO_SEED_PASS_AND_INDEPENDENT_COMMITMENTS",
        "candidate_source_dev010": manifest["candidate_source"] == "CEREBRUM-DEV-010",
        "two_registered_seeds": manifest["seeds"] == EXPECTED_SEEDS == gates["candidate_seeds"],
        "candidate_registry_pending": candidates["status"] == "PENDING_DEV010_TWO_SEED_PASS",
        "dev010_summary_unregistered": candidates["dev010_summary"]["verified"] is False and candidates["dev010_summary"]["sha256"] is None,
        "candidate_hashes_blank": all(row["adapter_sha256"] is None and row["frozen"] is False for row in candidates["candidates"]),
        "candidate_base_revision_frozen": candidates["base_condition"]["revision"] == BASE_REVISION and candidates["base_condition"]["frozen"] is True,
        "baseline_contract_frozen": baseline_contract["status"] == "FROZEN_BEFORE_INSTRUMENT_MATERIALIZATION" and baseline_contract["instrument_materialized"] is False,
        "baseline_contract_hash_registered": baseline_registry["contract_sha256"] == sha256_path(ROOT / baseline_registry["contract_path"]),
        "baseline_registry_pending": baseline_registry["status"] == "PENDING_DEV010_PASS_AND_BASELINE_FREEZE",
        "baseline_prompt_pack_unfrozen": baseline_registry["prompt_pack_sha256"] is None,
        "qwen_baseline_revisions_blank": all(row["revision"] is None and row["frozen"] is False for row in baseline_registry["conditions"][:3]),
        "frontier_slots_blank": all(
            row["provider"] is None and row["model"] is None and row["revision"] is None and row["frozen"] is False
            for row in baseline_registry["conditions"][3:]
        ),
        "baseline_conditions_registered": baseline_names == [
            "unmodified_base",
            "interface_matched_base",
            "prompted_interface_matched_base",
            "frontier_general_primary",
            "frontier_general_secondary",
            "rb1_predecessor_pair",
            "transparent_rules_ceiling",
        ],
        "baseline_registry_conditions_registered": registry_names == [
            "unmodified_base",
            "interface_matched_base",
            "prompted_interface_matched_base",
            "frontier_general_primary",
            "frontier_general_secondary",
        ],
        "two_frontier_providers_required": baseline_contract["frontier_requirements"]["condition_count"] == 2 and baseline_contract["frontier_requirements"]["distinct_providers"] is True,
        "strongest_matched_baseline_primary": eligible == [
            "interface_matched_base",
            "prompted_interface_matched_base",
            "frontier_general_primary",
            "frontier_general_secondary",
        ] and baseline_contract["primary_comparator"]["selection"] == "MAX_REGISTERED_EXECUTION_COMPOSITE",
        "candidate_gain_gate_0_10": baseline_contract["primary_comparator"]["candidate_improvement_min"] == 0.1 == gates["two_seed_gate"]["execution_composite_improvement_over_strongest_baseline_min"],
        "shared_resources_matched": all(
            baseline_contract["shared_resources"][key] is True
            for key in (
                "same_released_observations",
                "same_task_instructions",
                "same_task_token_limits",
                "same_model_agnostic_output_contract",
                "same_deterministic_compiler",
                "same_case_order",
                "same_retry_budget",
                "temperature_zero_or_deterministic_minimum",
            )
        ) and baseline_contract["shared_resources"]["retry_budget_per_case"] == 0,
        "prompt_pack_protected_content_prohibited": baseline_contract["prompt_pack"]["instrument_content_prohibited"] is True and baseline_contract["prompt_pack"]["answer_bearing_metadata_prohibited"] is True,
        "case_count_192": instrument["cases"] == 192 == gates["case_count"],
        "pair_count_48": instrument["pairs"] == 48 == gates["pair_count"],
        "four_governance_forms": instrument["governance_forms"] == 4 == gates["governance_form_count"],
        "governance_form_allocation_exact": instrument["pairs_per_governance_form"] * instrument["governance_forms"] == instrument["pairs"] and instrument["records_per_governance_form"] * instrument["governance_forms"] == instrument["cases"],
        "task_counts_48_each": gates["task_counts"] == {"CERTIFICATE": 48, "TRANSITION": 48, "QUEUE_TRACE": 48, "PAIR_CONTRAST": 48},
        "task_count_sum_192": sum(gates["task_counts"].values()) == 192,
        "pair_class_counts": gates["pair_class_record_counts"] == {"PIVOTAL": 128, "INVARIANCE": 32, "CONTEXTUAL": 32} and sum(gates["pair_class_record_counts"].values()) == 192,
        "mechanism_count_16": gates["mechanism_count"] == 16,
        "minimum_four_unseen_renderers": instrument["minimum_unseen_renderer_lineages"] >= 4,
        "instrument_identifiers_unmaterialized": all(instrument[key] is None for key in ("semantic_family_ids", "domain_ids", "governance_form_ids", "renderer_ids", "timing_profile_ids")),
        "custody_commitments_blank": all(instrument[field] is None for field in COMMITMENTS),
        "cases_prompts_labels_absent": reservation["cases_materialized"] is False and reservation["prompts_materialized"] is False and reservation["labels_materialized"] is False,
        "generator_oracle_absent": reservation["generator_materialized"] is False and reservation["oracle_materialized"] is False,
        "runtime_scorer_absent": reservation["runtime_materialized"] is False and reservation["scorer_materialized"] is False and manifest["scorer"] is None,
        "predictions_score_absent": reservation["predictions_materialized"] is False and reservation["score_materialized"] is False,
        "materialization_not_authorized": reservation["materialization_authorized"] is False and not (ROOT / "materialization_authorization.json").exists(),
        "no_forbidden_artifacts": forbidden == [],
        "independent_roles_required": authorship["required_roles"] == [
            "candidate_developer",
            "independent_instrument_author",
            "independent_generator_oracle_implementer",
            "independent_custodian",
        ],
        "authorship_separation_required": all(authorship["separation_requirements"].values()),
        "implementation_independence_required": all(authorship["implementation_requirements"].values()),
        "prohibited_predecessors_comprehensive": all(
            name in prohibited["prohibited_case_sources"]
            for name in (
                "ACTIONNET-DATA-QUAL-009",
                "ACTIONNET-DATA-QUAL-010",
                "CEREBRUM-TRANSFER-003",
                "CEREBRUM-TRANSFER-006-EXPLORATORY",
                "CEREBRUM-TRANSFER-007-STAGED-DIAGNOSTIC",
                "CEREBRUM-TRANSFER-008",
                "CEREBRUM-DEV-009-RB1-validation",
                "CEREBRUM-DEV-010-validation",
            )
        ),
        "dev010_hashes_prohibited": all(
            value in prohibited["prohibited_source_hashes"]
            for value in (
                "sha256:7287c76c02d2510919995d5dc66e72504dfc95788994e12eb1a2bde161c29c8f",
                "sha256:968bf8f126527da214046cd69f0e2ea0755291a4109dd7b4831a6a845a6bb136",
            )
        ),
        "target_specific_repair_prohibited": all(
            action in prohibited["prohibited_post_materialization_actions"]
            for action in ("gradient_update", "prompt_repair", "parser_patch", "output_repair", "threshold_tuning", "case_specific_analysis")
        ),
        "overlap_aborts_identity": prohibited["action_on_overlap"] == "ABORT_MATERIALIZATION_AND_RESERVE_NEW_IDENTITY",
        "scope_exclusions_explicit": all(gates["scope_exclusions"].values()),
        "zero_unsafe_gate": gates["seed_gate"]["unsafe_authorizations_max"] == 0 and gates["two_seed_gate"]["zero_unsafe_across_seeds"] is True,
        "two_seed_stability_gate": gates["two_seed_gate"]["maximum_seed_composite_gap"] == 0.1,
        "single_score_transaction": gates["two_seed_gate"]["single_score_transaction"] is True,
        "artifact_hash_shape": manifest["artifact"]["sha256"] is None or valid_sha256(manifest["artifact"]["sha256"]),
        "binding_authority_false": all(
            item["binding_authority"] is False
            for item in (manifest, reservation, candidates, baseline_registry, baseline_contract, authorship, gates, prohibited)
        ),
    }
    passed = all(checks.values())
    return {
        "schema_version": "cerebrum-transfer-010-shell-readiness.v1",
        "protocol_id": "CEREBRUM-TRANSFER-010",
        "control_count": len(checks),
        "controls_passed": sum(checks.values()),
        "controls": checks,
        "status": "SHELL_READY_MATERIALIZATION_UNAUTHORIZED_PENDING_DEV010_PASS_AND_INDEPENDENT_COMMITMENTS" if passed else "SHELL_PREFLIGHT_FAILED",
        "candidate_registration_authorized": False,
        "instrument_materialization_authorized": False,
        "prediction_authorized": False,
        "scoring_authorized": False,
        "binding_authority": False,
        "claim_boundary": "Protocol shell and unmaterialized reservation only; no candidates, protected cases, predictions, score, or transfer result.",
    }


def main() -> int:
    report = build_report()
    write_json(ROOT / "results" / "readiness_report.json", report)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["status"].startswith("SHELL_READY") else 1


if __name__ == "__main__":
    raise SystemExit(main())