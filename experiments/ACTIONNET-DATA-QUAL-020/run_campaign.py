#!/usr/bin/env python3
"""Materialize and qualify ACTIONNET-DATA-QUAL-020."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from actionnet020 import DATASET_ID, PROTOCOL_ID, RESULT_ID, canonical, generate


ROOT = Path(__file__).resolve().parent


def sha(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(canonical(row) + "\n" for row in rows), encoding="utf-8")


def main() -> int:
    predecessor = ROOT.parent / "ACTIONNET-DATA-QUAL-019" / "results" / "qualification_report.json"
    if not predecessor.is_file():
        raise SystemExit("missing ACTIONNET-DATA-QUAL-019 qualification report")
    previous = json.loads(predecessor.read_text(encoding="utf-8"))
    if previous.get("status") != "READY_FOR_CEREBRUM_DEV019_DIAGNOSTIC":
        raise SystemExit("ACTIONNET-DATA-QUAL-019 is not qualified")
    generated = generate()
    repeated = generate()
    controls = dict(generated["controls"])
    controls["byte_deterministic_generation"] = canonical(generated) == canonical(repeated)
    paths = {
        "calibration": ROOT / "dataset" / "format_calibration.jsonl",
        "heldout_validation": ROOT / "dataset" / "heldout_format_validation.jsonl",
        "calibration_trajectories": ROOT / "oracle" / "calibration_trajectories.jsonl",
        "validation_trajectories": ROOT / "oracle" / "validation_trajectories.jsonl",
        "lineages": ROOT / "lineage" / "lineages.json",
        "reservation": ROOT / "oracle" / "reservation.json",
    }
    write_jsonl(paths["calibration"], generated["calibration"])
    write_jsonl(paths["heldout_validation"], generated["heldout_validation"])
    write_jsonl(paths["calibration_trajectories"], generated["calibration_trajectories"])
    write_jsonl(paths["validation_trajectories"], generated["validation_trajectories"])
    write_json(paths["lineages"], {
        "schema_version": "actionnet-lineage-registry.v20",
        "records": generated["lineages"],
    })
    write_json(paths["reservation"], generated["protected"])
    status = "READY_FOR_CEREBRUM_DEV020_INTERFACE_CALIBRATION" if all(controls.values()) else "HOLD_FOR_REPAIR"
    report = {
        "schema_version": "actionnet-data-qualification-report.v20",
        "protocol_id": PROTOCOL_ID,
        "result_id": RESULT_ID,
        "dataset_id": DATASET_ID,
        "status": status,
        "control_count": len(controls),
        "controls_passed": sum(controls.values()),
        "controls": controls,
        "audits": generated["audits"],
        "source_grounded": False,
        "human_domain_review": False,
        "independent_generator_implementation": False,
        "binding_authority": False,
        "claim_boundary": (
            "Fresh project-authored synthetic interface-calibration data only; no learned repair, "
            "transfer, production authority, or IGI claim."
        ),
    }
    report_path = ROOT / "results" / "qualification_report.json"
    write_json(report_path, report)
    artifacts = [*paths.values(), report_path]
    manifest = {
        "schema_version": "result-manifest.v1",
        "result_id": RESULT_ID,
        "experiment_id": PROTOCOL_ID,
        "status": status,
        "artifacts": {path.relative_to(ROOT).as_posix(): sha(path) for path in artifacts},
        "claim_boundary": report["claim_boundary"],
    }
    manifest["result_hash"] = "sha256:" + hashlib.sha256(canonical(manifest).encode("utf-8")).hexdigest()
    write_json(ROOT / "results" / "result_manifest.json", manifest)
    print(json.dumps({
        "protocol_id": PROTOCOL_ID,
        "status": status,
        "controls_passed": sum(controls.values()),
        "control_count": len(controls),
        "training_records": 0,
        "calibration_scenarios": generated["audits"]["calibration"]["scenarios"],
        "calibration_predictions": generated["audits"]["calibration"]["records"],
        "heldout_scenarios": generated["audits"]["heldout_validation"]["scenarios"],
        "heldout_records_sealed": generated["audits"]["heldout_validation"]["records"],
    }, indent=2, sort_keys=True))
    return 0 if status.startswith("READY") else 1


if __name__ == "__main__":
    raise SystemExit(main())
