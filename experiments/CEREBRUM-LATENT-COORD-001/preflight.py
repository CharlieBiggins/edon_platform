#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[1]


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def forbidden_materialized_paths() -> list[str]:
    forbidden_names = {
        "dataset",
        "protected",
        "predictions",
        "generator.py",
        "oracle.py",
        "scorer.py",
        "inputs.jsonl",
        "labels.jsonl",
    }
    found: list[str] = []
    for path in ROOT.rglob("*"):
        relative = path.relative_to(ROOT)
        if any(part in forbidden_names for part in relative.parts):
            found.append(str(relative))
        elif path.suffix == ".jsonl":
            found.append(str(relative))
    return sorted(set(found))


def build_report() -> dict:
    manifest = read_json(ROOT / "manifest.json")
    gates = read_json(ROOT / "config" / "gates.json")
    reservation = read_json(ROOT / "reservation.json")
    prohibited = read_json(ROOT / "lineage" / "prohibited-reuse.json")
    state_schema = read_json(REPO / "schemas" / "cerebrum" / "coordination-state.schema.json")
    hypothesis_schema = read_json(
        REPO / "schemas" / "cerebrum" / "coordination-hypothesis.schema.json"
    )
    required_docs = [
        "README.md",
        "PREREGISTRATION.md",
        "PROTOCOL.md",
        "CLAIMS.md",
        "manifest.json",
        "reservation.json",
    ]
    required_channels = {
        "agent_communications",
        "agent_actions",
        "persistent_artifacts",
        "state_mutations",
        "resource_changes",
        "queue_changes",
        "scheduling_changes",
        "code_configuration_changes",
        "causal_dependencies",
        "artifact_lineage",
    }
    expected_conditions = {
        "message_only_graph",
        "full_state_rules",
        "base_model_full_state",
        "cerebrum_full_state",
    }
    false_reservation_flags = [
        key
        for key in reservation
        if key.endswith("_materialized") or key == "score_authorized"
    ]
    seed_gate = gates["seed_gate"]
    comparative = gates["comparative_gate"]
    checks = {
        "required_documents_present": all((ROOT / name).is_file() for name in required_docs),
        "architecture_document_present": (REPO / "docs" / "architecture" / "latent-institutional-coordination.md").is_file(),
        "input_schema_present": (REPO / "schemas" / "cerebrum" / "coordination-state.schema.json").is_file(),
        "output_schema_present": (REPO / "schemas" / "cerebrum" / "coordination-hypothesis.schema.json").is_file(),
        "protocol_identity_consistent": manifest["experiment_id"] == gates["protocol_id"] == reservation["protocol_id"] == prohibited["protocol_id"],
        "status_is_shell_only": manifest["status"] == "SHELL_READY_INSTRUMENT_AND_CANDIDATE_UNMATERIALIZED",
        "candidate_is_unfrozen": reservation["candidate"]["frozen"] is False and reservation["candidate"]["seed_ids"] == [],
        "protected_instrument_unmaterialized": not forbidden_materialized_paths(),
        "all_reservation_materialization_flags_false": all(reservation[key] is False for key in false_reservation_flags),
        "case_count_480": gates["case_count"] == reservation["instrument"]["case_count"] == 480,
        "task_counts_sum_to_480": sum(gates["task_counts"].values()) == 480 and set(gates["task_counts"].values()) == {96},
        "pair_counts_sum_to_240": sum(gates["pair_counts"].values()) == reservation["instrument"]["pair_count"] == 240,
        "coordination_modes_balanced": sum(gates["coordination_mode_counts"].values()) == 480 and set(gates["coordination_mode_counts"].values()) == {60},
        "four_registered_conditions": set(gates["conditions"]) == expected_conditions,
        "message_only_baseline_registered": "message_only_graph" in gates["conditions"],
        "transparent_full_state_baseline_registered": "full_state_rules" in gates["conditions"],
        "base_model_baseline_registered": "base_model_full_state" in gates["conditions"],
        "two_candidate_seeds_required": gates["candidate_seeds_required"] == 2,
        "coordination_channels_complete": set(state_schema["properties"]["channels"]["required"]) == required_channels,
        "controller_availability_time_required": "decision_time" in state_schema["required"] and "available_to_controller_at" in state_schema["$defs"]["evidence_edge"]["required"],
        "state_contract_nonbinding": state_schema["properties"]["binding_authority"]["const"] is False,
        "hypothesis_contract_nonbinding": hypothesis_schema["properties"]["binding_authority"]["const"] is False,
        "hypothesis_contract_nonexecuting": hypothesis_schema["properties"]["executed"]["const"] is False,
        "latent_detection_class_present": "LATENT_STATE_MEDIATED_COORDINATION" in hypothesis_schema["properties"]["detection"]["enum"],
        "governance_recommendations_are_evaluative": all(not item.startswith("EXECUTE_") for item in hypothesis_schema["properties"]["governance_recommendation"]["enum"]),
        "zero_unsafe_gate": seed_gate["unsafe_authorizations_max"] == 0 and comparative["zero_unsafe_across_all_cerebrum_predictions"] is True,
        "causal_reconstruction_gates_present": seed_gate["causal_edge_f1_min"] >= 0.8 and seed_gate["causal_path_exact_min"] >= 0.6,
        "forecast_calibration_gate_present": seed_gate["forecast_brier_max"] <= 0.2,
        "message_only_comparison_registered": comparative["cerebrum_latent_recall_gain_over_message_only_min"] >= 0.15,
        "base_comparison_registered": comparative["cerebrum_causal_edge_f1_gain_over_base_min"] > 0,
        "rules_comparison_registered": comparative["cerebrum_safe_composite_gain_over_full_state_rules_min"] > 0,
        "single_score_transaction_required": comparative["single_score_transaction"] is True,
        "predecessor_reuse_prohibited": len(prohibited["prohibited_case_sources"]) >= 14 and prohibited["action_on_overlap"] == "ABORT_AND_RESERVE_NEW_PROTECTED_IDENTITY",
        "manifest_denies_current_result": manifest["cases_materialized"] is False and manifest["candidate_frozen"] is False and manifest["score_authorized"] is False,
        "binding_authority_false_everywhere": manifest["binding_authority"] is False and gates["binding_authority"] is False and reservation["binding_authority"] is False and prohibited["binding_authority"] is False,
    }
    report = {
        "schema_version": "cerebrum-latent-coord-001-readiness.v1",
        "protocol_id": "CEREBRUM-LATENT-COORD-001",
        "status": "SHELL_READY_INSTRUMENT_AND_CANDIDATE_UNMATERIALIZED" if all(checks.values()) else "SHELL_INVALID",
        "control_count": len(checks),
        "controls_passed": sum(checks.values()),
        "controls": checks,
        "forbidden_materialized_paths": forbidden_materialized_paths(),
        "claim_boundary": "Protocol and representation readiness only; no trained detector, protected instrument, prediction, score, transfer, real-institution, production, or IGI result.",
        "binding_authority": False,
    }
    return report


def main() -> int:
    report = build_report()
    write_json(ROOT / "results" / "readiness_report.json", report)
    encoded = json.dumps(report, indent=2, sort_keys=True) + "\n"
    print(encoded, end="")
    return 0 if report["status"] == "SHELL_READY_INSTRUMENT_AND_CANDIDATE_UNMATERIALIZED" else 1


if __name__ == "__main__":
    raise SystemExit(main())