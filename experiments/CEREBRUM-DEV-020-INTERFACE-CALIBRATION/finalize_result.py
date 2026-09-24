#!/usr/bin/env python3
"""Freeze the completed DEV-020 result and emit a heldout error audit.

This is deliberately CPU-only. It does not regenerate predictions, reopen
selection, or modify either scored result.
"""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from dev020_common import CONFIG, ROOT, canonical, read_json, read_jsonl, sha256_path, write_json
from interface_analysis import CERTIFICATE_FIELDS, evaluate


RESULTS = ROOT / "results"
PREPARED = ROOT / "prepared"


def _required_files() -> dict[str, Path]:
    return {
        "config": CONFIG,
        "calibration_input": PREPARED / "format-calibration-384.jsonl",
        "calibration_predictions": RESULTS / "calibration-predictions.jsonl",
        "calibration_prediction_freeze": RESULTS / "calibration-prediction-freeze.json",
        "calibration_result": RESULTS / "dev020-calibration-result.json",
        "selection_freeze": RESULTS / "representation-selection-freeze.json",
        "validation_input": PREPARED / "heldout-selected-validation-192.jsonl",
        "validation_predictions": RESULTS / "validation-predictions.jsonl",
        "validation_prediction_freeze": RESULTS / "validation-prediction-freeze.json",
        "interface_result": RESULTS / "dev020-interface-result.json",
    }


def _field_differences(expected: dict[str, Any], actual: dict[str, Any]) -> list[str]:
    return [
        field for field in CERTIFICATE_FIELDS
        if canonical(expected.get(field)) != canonical(actual.get(field))
    ]


def build_error_audit(
    calibration_rows: list[dict[str, Any]],
    calibration_predictions: list[dict[str, Any]],
    validation_rows: list[dict[str, Any]],
    validation_predictions: list[dict[str, Any]],
    selected: str,
    baseline: str,
    fidelity_condition: str,
) -> dict[str, Any]:
    calibration = evaluate(calibration_rows, calibration_predictions)
    validation = evaluate(validation_rows, validation_predictions)
    by_scenario: dict[str, dict[str, dict[str, Any]]] = defaultdict(dict)
    for row in validation:
        by_scenario[row["scenario_id"]][row["condition"]] = row

    selected_rows = [row for row in validation if row["condition"] == selected]
    raw_rows = [row for row in validation if row["condition"] == baseline]
    fidelity_calibration = [row for row in calibration if row["condition"] == fidelity_condition]
    fidelity_validation = [row for row in validation if row["condition"] == fidelity_condition]

    failures = []
    unsafe = []
    for row in selected_rows:
        pair = by_scenario[row["scenario_id"]]
        raw = pair[baseline]
        detail = {
            "scenario_id": row["scenario_id"],
            "case_id": row["case_id"],
            "mechanism": row["mechanism"],
            "expected_decision": row["expected"].get("decision"),
            "actual_decision": row["actual"].get("decision"),
            "expected_semantic_state": row["expected"].get("semantic_state"),
            "actual_semantic_state": row["actual"].get("semantic_state"),
            "differing_fields": _field_differences(row["expected"], row["actual"]),
            "unsafe_authorization": row["unsafe_authorization"],
            "raw_and_selected_outputs_identical": canonical(raw["actual"]) == canonical(row["actual"]),
        }
        if not row["exact"]:
            failures.append(detail)
        if row["unsafe_authorization"]:
            unsafe.append(detail)

    mechanisms: dict[str, dict[str, int]] = {}
    for mechanism in sorted({row["mechanism"] for row in selected_rows}):
        rows = [row for row in selected_rows if row["mechanism"] == mechanism]
        mechanisms[mechanism] = {
            "examples": len(rows),
            "exact": sum(row["exact"] for row in rows),
            "decision_correct": sum(row["decision_correct"] for row in rows),
            "unsafe_authorizations": sum(row["unsafe_authorization"] for row in rows),
        }

    field_failure_counts = Counter(
        field for detail in failures for field in detail["differing_fields"]
    )
    paired = [
        (records[baseline], records[selected])
        for records in by_scenario.values()
        if baseline in records and selected in records
    ]
    fidelity_all = fidelity_calibration + fidelity_validation
    return {
        "schema_version": "cerebrum-dev020-final-error-audit.v1",
        "protocol_id": "CEREBRUM-DEV-020-INTERFACE-CALIBRATION",
        "selected_representation": selected,
        "heldout": {
            "scenarios": len(selected_rows),
            "selected_exact": sum(row["exact"] for row in selected_rows),
            "selected_decision_correct": sum(row["decision_correct"] for row in selected_rows),
            "selected_unsafe_authorizations": sum(row["unsafe_authorization"] for row in selected_rows),
            "raw_exact": sum(row["exact"] for row in raw_rows),
            "raw_decision_correct": sum(row["decision_correct"] for row in raw_rows),
            "raw_unsafe_authorizations": sum(row["unsafe_authorization"] for row in raw_rows),
            "raw_selected_decision_agreement": sum(
                before["actual"].get("decision") == after["actual"].get("decision")
                for before, after in paired
            ),
            "raw_selected_exact_output_agreement": sum(
                canonical(before["actual"]) == canonical(after["actual"])
                for before, after in paired
            ),
            "failure_count": len(failures),
            "failures": failures,
            "unsafe_failure_count": len(unsafe),
            "unsafe_failures": unsafe,
            "field_failure_counts": dict(sorted(field_failure_counts.items())),
            "by_mechanism": mechanisms,
        },
        "authenticated_decision_fidelity": {
            "calibration_examples": len(fidelity_calibration),
            "validation_examples": len(fidelity_validation),
            "combined_examples": len(fidelity_all),
            "decision_preserved": sum(row["decision_correct"] for row in fidelity_all),
            "exact_certificates": sum(row["exact"] for row in fidelity_all),
            "unsafe_authorizations": sum(row["unsafe_authorization"] for row in fidelity_all),
            "field_failure_counts": dict(sorted(Counter(
                field
                for row in fidelity_all
                for field, correct in row["field_correct"].items()
                if not correct
            ).items())),
        },
        "interpretation": {
            "interface_stable": True,
            "interface_improved_reasoning": (
                sum(row["decision_correct"] for row in selected_rows)
                > sum(row["decision_correct"] for row in raw_rows)
            ),
            "familiar_augmented_is_behaviorally_equivalent_to_raw_on_heldout": all(
                canonical(before["actual"]) == canonical(after["actual"])
                for before, after in paired
            ),
            "immutable_certificate_copying_supported": all(row["decision_correct"] for row in fidelity_all),
            "unsafe_failure_repair_still_required": any(row["unsafe_authorization"] for row in selected_rows),
            "next_gate": "native executable temporal-program training with an independent interpreter",
        },
        "training_steps": 0,
        "transfer_authorized": False,
        "binding_authority": False,
        "claim_boundary": (
            "Post-hoc error audit of frozen DEV-020 predictions. It freezes the validated input interface and "
            "identifies remaining failures; it is not a training, transfer, deployment, authority, or IGI result."
        ),
    }


def main() -> int:
    files = _required_files()
    missing = [name for name, path in files.items() if not path.is_file()]
    if missing:
        raise SystemExit(f"DEV-020 is not complete; missing: {', '.join(missing)}")

    config = read_json(CONFIG)
    result = read_json(files["interface_result"])
    selection = read_json(files["selection_freeze"])
    selected = result.get("selected_representation")
    if result.get("status") != "INTERFACE_CALIBRATION_SIGNAL" or result.get("passed") is not True:
        raise SystemExit("DEV-020 final interface result did not pass")
    if selected != selection.get("selected_representation"):
        raise SystemExit("selected representation differs between result and selection freeze")

    calibration_freeze = read_json(files["calibration_prediction_freeze"])
    validation_freeze = read_json(files["validation_prediction_freeze"])
    controls = {
        "calibration_input_bound": calibration_freeze.get("input_sha256") == sha256_path(files["calibration_input"]),
        "calibration_predictions_bound": calibration_freeze.get("predictions_sha256") == sha256_path(files["calibration_predictions"]),
        "validation_input_bound": validation_freeze.get("input_sha256") == sha256_path(files["validation_input"]),
        "validation_predictions_bound": validation_freeze.get("predictions_sha256") == sha256_path(files["validation_predictions"]),
        "selection_bound": result.get("selection_freeze_sha256") == sha256_path(files["selection_freeze"]),
        "calibration_result_bound": result.get("calibration_result_sha256") == sha256_path(files["calibration_result"]),
        "validation_freeze_bound": result.get("validation_prediction_freeze_sha256") == sha256_path(files["validation_prediction_freeze"]),
        "selected_representation_validated": result.get("representation_validated") is True,
        "decision_fidelity_validated": result.get("decision_fidelity_validated") is True,
        "zero_training_steps": result.get("training_steps") == 0,
    }
    if not all(controls.values()):
        failed = [name for name, passed in controls.items() if not passed]
        raise SystemExit(f"DEV-020 freeze controls failed: {', '.join(failed)}")

    audit = build_error_audit(
        read_jsonl(files["calibration_input"]),
        read_jsonl(files["calibration_predictions"]),
        read_jsonl(files["validation_input"]),
        read_jsonl(files["validation_predictions"]),
        selected,
        config["baseline_representation"],
        config["fidelity_condition"],
    )
    audit["controls"] = controls
    audit["controls_passed"] = sum(controls.values())
    audit["control_count"] = len(controls)
    audit_path = RESULTS / "dev020-final-error-audit.json"
    write_json(audit_path, audit)

    freeze = {
        "schema_version": "cerebrum-dev020-result-freeze.v1",
        "protocol_id": config["protocol_id"],
        "status": "DEV020_INTERFACE_FROZEN_FOR_PROGRAM001",
        "selected_representation": selected,
        "source_hashes": {name: sha256_path(path) for name, path in sorted(files.items())},
        "error_audit_sha256": sha256_path(audit_path),
        "training_steps": 0,
        "transfer_authorized": False,
        "binding_authority": False,
        "claim_boundary": "Immutable local freeze of the completed DEV-020 interface result for Program-001 lineage only.",
    }
    write_json(RESULTS / "dev020-result-freeze.json", freeze)
    print(json.dumps({"audit": audit, "freeze": freeze}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())