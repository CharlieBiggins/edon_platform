#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

from mlgw_program import EVIDENCE_CLASSES, ROOT, read_json, read_jsonl, sha256_path, validate_ledger, write_json
from run_synthetic_rehearsal import synthetic_world
from simulator import simulate
from mlgw_program import compare_episodes


REQUIRED_DOCS = [
    "README.md", "PROTOCOL.md", "CLAIMS.md", "PROGRAM_ROADMAP.md",
    "DATA_ACQUISITION.md", "CUSTODY_AND_SECURITY.md", "PILOT_PROTOCOL.md",
    "STATISTICAL_ANALYSIS.md", "manifest.json",
]
REQUIRED_CODE = [
    "mlgw_program.py", "simulator.py", "capture_record.py", "freeze_timeline.py",
    "score_episodes.py", "run_synthetic_rehearsal.py", "preflight.py",
]
REQUIRED_SCHEMAS = [
    "evidence-record.schema.json", "source-record.schema.json",
    "storm-world.schema.json", "controller-recommendation.schema.json",
    "episode-result.schema.json",
]


def main() -> int:
    manifest = read_json(ROOT / "manifest.json")
    protocol = read_json(ROOT / "config" / "protocol.json")
    assumptions = read_json(ROOT / "config" / "planning_assumptions.json")
    controllers = read_json(ROOT / "config" / "controller_registry.json")
    storms = read_json(ROOT / "config" / "storm_registry.json")
    sources = read_json(ROOT / "public_sources" / "source_registry.json")
    ledger = read_jsonl(ROOT / "data" / "public_event_ledger.jsonl")
    chain = validate_ledger(ledger)
    schema_values = [read_json(ROOT / "schemas" / name) for name in REQUIRED_SCHEMAS]
    source_ids = [row["source_id"] for row in sources["sources"]]
    record_ids = [row["record_id"] for row in ledger]
    snapshot = next((row for row in ledger if row["record_id"] == "MLGW-OUTAGE-20260824T0738-CDT"), None)
    rehearsal_actual = simulate(synthetic_world(), "actual_mlgw_replay")
    rehearsal_candidate = simulate(synthetic_world(), "critical_biggest_return")
    rehearsal_comparison = compare_episodes(rehearsal_actual, rehearsal_candidate)
    checks = {
        "required_documents_present": all((ROOT / name).is_file() for name in REQUIRED_DOCS),
        "required_code_present": all((ROOT / name).is_file() for name in REQUIRED_CODE),
        "required_schemas_present": all((ROOT / "schemas" / name).is_file() for name in REQUIRED_SCHEMAS),
        "schemas_parse_as_json": len(schema_values) == len(REQUIRED_SCHEMAS),
        "protocol_identity": protocol["protocol_id"] == "EDON-MLGW-OR-001",
        "manifest_identity": manifest["experiment_id"] == protocol["protocol_id"],
        "status_blocks_execution": manifest["status"] == "PROTOCOL_READY_BLOCKED_MISSING_MLGW_AUTHORIZATION_AND_AUTHORITATIVE_DATA",
        "unaffiliated_status_explicit": manifest["affiliation"] == "UNAFFILIATED_RESEARCH_PROPOSAL",
        "mlgw_authorization_false": manifest["mlgw_authorized"] is False,
        "protected_data_absent": manifest["protected_data_materialized"] is False,
        "binding_authority_false": manifest["binding_authority"] is False,
        "public_event_not_protected": manifest["event_anchor"]["protected"] is False,
        "public_event_not_prospective": manifest["event_anchor"]["prospective"] is False,
        "evidence_classes_frozen": set(protocol["evidence_classes"]) == EVIDENCE_CLASSES,
        "estimates_are_non_authoritative": all(
            row["evidence_class"] in {"ESTIMATED", "TARGET"} and row["authoritative"] is False
            for row in assumptions["records"]
        ),
        "ledger_chain_valid": chain["valid"] is True,
        "ledger_ids_unique": len(record_ids) == len(set(record_ids)),
        "ledger_training_ineligible": all(row["training_eligible"] is False for row in ledger),
        "ledger_has_no_estimates_or_targets": all(row["evidence_class"] in {"OBSERVED", "DERIVED"} for row in ledger),
        "public_records_not_yet_authoritative": all(row["authoritative"] is False for row in ledger),
        "source_ids_unique": len(source_ids) == len(set(source_ids)),
        "source_bytes_not_misrepresented": all(
            (row["bytes_archived"] and isinstance(row["sha256"], str))
            or (not row["bytes_archived"] and row["sha256"] is None)
            for row in sources["sources"]
        ),
        "official_0738_snapshot_registered": snapshot is not None and snapshot["payload"].get("customers_without_power") == 49420,
        "six_controller_conditions_registered": len(controllers["controllers"]) == 6,
        "controller_resources_matched": controllers["equal_resources_required"] is True,
        "controller_information_matched": controllers["equal_information_required"] is True,
        "controller_budget_matched": controllers["equal_budget_required"] is True,
        "future_shadow_unmaterialized": storms["future_live_event"]["materialized"] is False,
        "safety_is_zero_tolerance": all(
            tier["unsafe_recommendations_max"] == 0 for tier in protocol["tiers"].values()
        ),
        "monte_carlo_requires_calibration": protocol["monte_carlo"]["requires_calibrated_uncertainty_model"] is True,
        "synthetic_rehearsal_matched": rehearsal_comparison["valid_matched_resources"] is True,
        "synthetic_rehearsal_safe": rehearsal_comparison["candidate_safety_gate_passed"] is True,
        "synthetic_rehearsal_exercises_difference": rehearsal_comparison["customer_outage_hours_reduction"] is not None,
    }
    passed = all(checks.values())
    report = {
        "schema_version": "edon-mlgw-or-readiness.v1",
        "protocol_id": protocol["protocol_id"],
        "control_count": len(checks),
        "controls_passed": sum(checks.values()),
        "controls": checks,
        "status": manifest["status"] if passed else "PACKAGE_PREFLIGHT_FAILED",
        "ledger": chain,
        "ledger_sha256": sha256_path(ROOT / "data" / "public_event_ledger.jsonl"),
        "source_count": len(sources["sources"]),
        "protected_execution_authorized": False,
        "live_shadow_authorized": False,
        "binding_authority": False,
        "claim_boundary": "Protocol readiness only. No MLGW authorization, authoritative internal dataset, calibrated simulator, controller execution, protected score, or operational result exists."
    }
    write_json(ROOT / "results" / "readiness_report.json", report)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())