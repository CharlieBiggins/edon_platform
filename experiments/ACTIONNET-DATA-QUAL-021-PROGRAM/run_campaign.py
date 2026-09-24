#!/usr/bin/env python3
"""Materialize and qualify ACTIONNET-DATA-QUAL-021-PROGRAM."""

from __future__ import annotations

import json
from collections import Counter

from actionnet021 import ROOT, canonical, generate
from program_ir import parse_program_a, parse_program_b, verify_program


def write_json(path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_jsonl(path, rows) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(canonical(row) + "\n" for row in rows), encoding="utf-8")


def main() -> int:
    generated = generate()
    verifications = []
    for split, rows in generated["rows"].items():
        trajectory_by_id = {
            trajectory["trajectory_id"]: trajectory
            for trajectory in generated["trajectories"][split]
        }
        for row in rows:
            trajectory = trajectory_by_id[row["metadata"]["trajectory_id"]]
            text = row["target"]["program"]
            left = parse_program_a(text)
            right = parse_program_b(text)
            verification = verify_program(
                text,
                row["input"]["program_source"]["initial_state"],
                row["input"]["program_source"]["submitted_events"],
                row["target"]["final_state"],
                row["target"]["certificate"],
            )
            verifications.append({
                "split": split,
                "case_id": row["case_id"],
                "parsers_identical": canonical(left) == canonical(right),
                **{key: value for key, value in verification.items() if isinstance(value, bool)},
                "trajectory_target_matches": (
                    canonical(row["target"]["final_state"]) == canonical(trajectory["final_state"])
                    and canonical(row["target"]["certificate"]) == canonical(trajectory["outcome"])
                ),
            })

    controls = dict(generated["controls"])
    controls.update({
        "all_oracle_programs_parse_twice": all(row["parse_valid"] and row["parsers_identical"] for row in verifications),
        "all_oracle_programs_verifier_accepted": all(row["accepted_by_verifier"] for row in verifications),
        "all_oracle_programs_exact": all(row["program_exact"] for row in verifications),
        "all_oracle_execution_states_exact": all(row["executed_state_exact"] for row in verifications),
        "all_oracle_certificates_exact": all(row["derived_certificate_exact"] for row in verifications),
        "zero_oracle_unsafe_authorizations": not any(row["unsafe_authorization"] for row in verifications),
        "trajectory_targets_bound": all(row["trajectory_target_matches"] for row in verifications),
        "all_decision_classes_in_every_split": all(
            set(Counter(row["metadata"]["decision"] for row in rows))
            == {"ABSTAIN", "ALLOW", "CONTESTED", "DENY", "INVALID"}
            for rows in generated["rows"].values()
        ),
    })
    for split, rows in generated["rows"].items():
        filename = {
            "train": "train.jsonl",
            "development_selection": "development_selection.jsonl",
            "untouched_confirmation": "untouched_confirmation.jsonl",
        }[split]
        write_jsonl(ROOT / "dataset" / filename, rows)
        write_jsonl(ROOT / "trajectories" / f"{split}.jsonl", generated["trajectories"][split])
    write_json(ROOT / "lineage" / "lineages.json", {
        "schema_version": "actionnet-lineage-registry.v21",
        "records": generated["lineages"],
    })
    report = {
        "schema_version": "actionnet-data-qualification-report.v21",
        "protocol_id": generated["protocol_id"],
        "result_id": generated["result_id"],
        "dataset_id": generated["dataset_id"],
        "status": "READY_FOR_CEREBRUM_END2END_PROGRAM_001" if all(controls.values()) else "HOLD",
        "passed": all(controls.values()),
        "controls": controls,
        "controls_passed": sum(controls.values()),
        "control_count": len(controls),
        "audits": generated["audits"],
        "verification_records": len(verifications),
        "training_records": len(generated["rows"]["train"]),
        "development_records": len(generated["rows"]["development_selection"]),
        "confirmation_records": len(generated["rows"]["untouched_confirmation"]),
        "selected_renderer": "FAMILIAR_AUGMENTED",
        "program_schema": "ACTIONNET_TEMPORAL_PROGRAM_V1",
        "transfer_authorized": False,
        "binding_authority": False,
        "claim_boundary": (
            "Fresh synthetic executable-program supervision qualified for a development experiment only; "
            "no model capability, transfer, production authority, or IGI claim."
        ),
    }
    write_json(ROOT / "results" / "qualification_report.json", report)
    write_json(ROOT / "results" / "result_manifest.json", {
        "schema_version": "result-manifest.v1",
        "protocol_id": generated["protocol_id"],
        "result_id": generated["result_id"],
        "status": report["status"],
    })
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())