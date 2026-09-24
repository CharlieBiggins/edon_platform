#!/usr/bin/env python3
from __future__ import annotations

import json

from transfer008 import ROOT, EXPECTED_SEEDS, forbidden_materialized_paths, read_json, sha256_path, write_json


REQUIRED_DOCS = [
    "README.md", "PREREGISTRATION.md", "PROTOCOL.md", "CLAIMS.md", "CUSTODY.md",
    "MATERIALIZATION_HANDOFF.md", "AMENDMENT-001-BASELINE-FAIRNESS.md", "manifest.json",
    "reservation.json", "candidate_registry.json", "baseline_registry.json",
]
REQUIRED_CODE = ["transfer008.py", "preflight.py", "register_candidates.py", "authorize_materialization.py"]
COMMITMENTS = [
    "generator_seed_commitment", "generator_source_commitment", "oracle_source_commitment",
    "input_commitment", "label_commitment", "overlap_audit_commitment",
]


def build_report() -> dict:
    manifest = read_json(ROOT / "manifest.json")
    gates = read_json(ROOT / "config" / "transfer-gates.json")
    reservation = read_json(ROOT / "reservation.json")
    candidates = read_json(ROOT / "candidate_registry.json")
    baseline_contract = read_json(ROOT / "config" / "baseline-contract.json")
    baseline_registry = read_json(ROOT / "baseline_registry.json")
    prohibited = read_json(ROOT / "lineage" / "prohibited-predecessors.json")
    scope = read_json(ROOT.parents[1] / "governance" / "igi-scope" / "EDON-IGI-SCOPE-001" / "scope.json")
    forbidden = forbidden_materialized_paths()
    instrument = reservation["instrument"]
    checks = {
        "required_documents_present": all((ROOT / name).is_file() for name in REQUIRED_DOCS),
        "required_code_present": all((ROOT / name).is_file() for name in REQUIRED_CODE),
        "baseline_contract_present": (ROOT / "config" / "baseline-contract.json").is_file(),
        "baseline_schema_present": (ROOT / "schemas" / "baseline-registry.schema.json").is_file(),
        "protocol_identity": manifest["experiment_id"] == "CEREBRUM-TRANSFER-008" == gates["protocol_id"],
        "status_is_reserved_and_blocked": manifest["status"] == "RESERVED_BLOCKED_PENDING_RB1_TWO_SEED_PASS_AND_INDEPENDENT_INSTRUMENT",
        "rb1_candidate_source": manifest["candidate_source"] == "CEREBRUM-DEV-009-RB1",
        "two_registered_seeds": manifest["seeds"] == EXPECTED_SEEDS == gates["candidate_seeds"],
        "candidate_registry_pending": candidates["status"] == "PENDING_RB1_TWO_SEED_PASS",
        "rb1_summary_unregistered": candidates["rb1_summary"]["verified"] is False and candidates["rb1_summary"]["sha256"] is None,
        "candidate_hashes_blank": all(row["adapter_sha256"] is None and row["frozen"] is False for row in candidates["candidates"]),
        "base_revision_unfrozen": candidates["base_condition"]["revision"] is None and candidates["base_condition"]["frozen"] is False,
        "baseline_amendment_frozen_before_materialization": baseline_contract["status"] == "FROZEN_BEFORE_INSTRUMENT_MATERIALIZATION" and baseline_contract["instrument_materialized"] is False,
        "baseline_registry_pending": baseline_registry["status"] == "PENDING_RB1_TWO_SEED_PASS",
        "baseline_contract_hash_registered": baseline_registry["contract_sha256"] == sha256_path(ROOT / baseline_registry["contract_path"]),
        "baseline_prompt_pack_unfrozen": baseline_registry["prompt_pack_sha256"] is None,
        "baseline_slots_blank": all(row["revision"] is None and row["adapter_sha256"] is None and row["frozen"] is False for row in baseline_registry["conditions"]),
        "baseline_conditions_registered": [row["condition"] for row in baseline_contract["conditions"]] == [
            "unmodified_base", "interface_matched_base", "prompted_interface_matched_base", "transparent_rules_ceiling",
        ],
        "baseline_registry_conditions_registered": [row["condition"] for row in baseline_registry["conditions"]] == [
            "unmodified_base", "interface_matched_base", "prompted_interface_matched_base",
        ],
        "raw_base_diagnostic_only": baseline_contract["primary_comparator"]["raw_unmodified_base_is_diagnostic_only"] is True,
        "strongest_matched_learned_comparator": baseline_contract["primary_comparator"]["eligible_conditions"] == [
            "interface_matched_base", "prompted_interface_matched_base",
        ] and baseline_contract["primary_comparator"]["selection"] == "MAX_REGISTERED_EXECUTION_COMPOSITE",
        "additive_improvement_gate_0_15": baseline_contract["primary_comparator"]["candidate_improvement_min"] == 0.15 == gates["two_seed_gate"]["execution_composite_improvement_over_base_min"],
        "shared_learned_resources_matched": all(baseline_contract["shared_learned_resources"][key] is True for key in (
            "same_base_revision", "same_observations", "same_task_instructions", "same_task_token_limits",
            "same_deterministic_compiler", "same_hardware_class", "same_case_order", "deterministic_decoding",
        )) and baseline_contract["shared_learned_resources"]["retry_budget_per_case"] == 0,
        "schema_constraint_shared_with_candidates": baseline_contract["shared_learned_resources"]["schema_constraint_applies_to"] == [
            "interface_matched_base", "prompted_interface_matched_base", "rb1_seed_26082491", "rb1_seed_26082492",
        ],
        "prompt_pack_instrument_content_prohibited": baseline_contract["prompt_pack"]["instrument_content_prohibited"] is True and baseline_contract["prompt_pack"]["answer_bearing_metadata_prohibited"] is True,
        "conditional_and_compiled_metrics_required": all(name in baseline_contract["required_metric_views"] for name in (
            "RAW_SCHEMA_VALIDITY", "CONDITIONAL_DECISION_ACCURACY_GIVEN_VALID_OUTPUT",
            "CONDITIONAL_SEMANTIC_ACCURACY_GIVEN_VALID_OUTPUT", "FINAL_COMPILED_ACCURACY",
        )),
        "case_count_reserved_192": instrument["cases"] == 192 == gates["case_count"],
        "task_counts_48_each": gates["task_counts"] == {"CERTIFICATE": 48, "TRANSITION": 48, "QUEUE_TRACE": 48, "PAIR_CONTRAST": 48},
        "task_count_sum_192": sum(gates["task_counts"].values()) == 192,
        "pair_class_counts_registered": gates["pair_class_record_counts"] == {"PIVOTAL": 128, "INVARIANCE": 32, "CONTEXTUAL": 32},
        "mechanism_count_16": gates["mechanism_count"] == 16,
        "instrument_identifiers_unmaterialized": all(instrument[key] is None for key in ("semantic_family_ids", "domain_ids", "renderer_ids", "timing_profile_ids")),
        "custody_commitments_blank": all(instrument[field] is None for field in COMMITMENTS),
        "cases_not_materialized": reservation["cases_materialized"] is False,
        "prompts_not_materialized": reservation["prompts_materialized"] is False,
        "labels_not_materialized": reservation["labels_materialized"] is False,
        "generator_and_oracle_not_materialized": reservation["generator_materialized"] is False and reservation["oracle_materialized"] is False,
        "runtime_not_materialized": reservation["runtime_materialized"] is False,
        "scorer_not_materialized": reservation["scorer_materialized"] is False and manifest["scorer"] is None,
        "predictions_and_score_not_materialized": reservation["predictions_materialized"] is False and reservation["score_materialized"] is False,
        "materialization_not_authorized": reservation["materialization_authorized"] is False and not (ROOT / "materialization_authorization.json").exists(),
        "no_forbidden_artifacts_in_shell": forbidden == [],
        "predecessor_protocols_prohibited": all(name in prohibited["prohibited_case_sources"] for name in (
            "CEREBRUM-TRANSFER-003", "CEREBRUM-TRANSFER-006-EXPLORATORY",
            "CEREBRUM-TRANSFER-007-STAGED-DIAGNOSTIC-smoke", "CEREBRUM-DEV-009-RB1-validation",
        )),
        "rb1_hashes_prohibited_from_reuse": "sha256:bec1faa6d76a7ab11facf8e8f3cf72674406dee123e9947c237ca18b4806e361" in prohibited["prohibited_source_hashes"],
        "overlap_action_aborts": prohibited["action_on_overlap"] == "ABORT_MATERIALIZATION_AND_RESERVE_NEW_IDENTITY",
        "zero_unsafe_gate": gates["seed_gate"]["unsafe_authorizations_max"] == 0,
        "single_score_transaction": gates["two_seed_gate"]["single_score_transaction"] is True,
        "scope001_transfer_anchors_preserved": sha256_path(ROOT / "manifest.json") == scope["transfer008_relation"]["manifest_sha256"] and sha256_path(ROOT / "reservation.json") == scope["transfer008_relation"]["reservation_sha256"] and sha256_path(ROOT / "config" / "transfer-gates.json") == scope["transfer008_relation"]["gates_sha256"],
        "binding_authority_false": manifest["binding_authority"] is False and reservation["binding_authority"] is False and candidates["binding_authority"] is False and baseline_registry["binding_authority"] is False and baseline_contract["binding_authority"] is False,
    }
    passed = all(checks.values())
    return {
        "schema_version": "cerebrum-transfer-008-shell-readiness.v1",
        "protocol_id": "CEREBRUM-TRANSFER-008",
        "control_count": len(checks),
        "controls_passed": sum(checks.values()),
        "controls": checks,
        "status": "SHELL_READY_MATERIALIZATION_UNAUTHORIZED_PENDING_RB1_PASS" if passed else "SHELL_PREFLIGHT_FAILED",
        "candidate_registration_authorized": False,
        "instrument_materialization_authorized": False,
        "prediction_authorized": False,
        "scoring_authorized": False,
        "binding_authority": False,
        "claim_boundary": "Protocol shell and unmaterialized reservation only; no candidates, cases, predictions, score, or transfer result."
    }


def main() -> int:
    report = build_report()
    write_json(ROOT / "results" / "readiness_report.json", report)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["status"].startswith("SHELL_READY") else 1


if __name__ == "__main__":
    raise SystemExit(main())