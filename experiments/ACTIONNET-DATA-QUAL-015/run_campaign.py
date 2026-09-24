#!/usr/bin/env python3
"""Materialize and qualify ACTIONNET-DATA-QUAL-015."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

from actionnet015 import DATASET_ID, PROTOCOL_ID, RESULT_ID, canonical, generate


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
    for source in ("ACTIONNET-DATA-QUAL-010", "ACTIONNET-DATA-QUAL-013", "ACTIONNET-DATA-QUAL-014"):
        subprocess.run(
            [sys.executable, "run_campaign.py"],
            cwd=ROOT.parent / source,
            check=True,
            stdout=subprocess.DEVNULL,
        )
    generated = generate()
    repeated = generate()
    controls = dict(generated["controls"])
    controls["byte_deterministic_generation"] = canonical(generated) == canonical(repeated)
    paths = {
        "train": ROOT / "dataset" / "train.jsonl",
        "development": ROOT / "dataset" / "development_selection.jsonl",
        "confirmation": ROOT / "dataset" / "untouched_confirmation.jsonl",
        "trajectories": ROOT / "oracle" / "canonical_trajectories.jsonl",
        "lineages": ROOT / "lineage" / "lineages.json",
        "reservation": ROOT / "oracle" / "reservation.json",
    }
    write_jsonl(paths["train"], generated["datasets"]["train"])
    write_jsonl(paths["development"], generated["datasets"]["development_selection"])
    write_jsonl(paths["confirmation"], generated["datasets"]["untouched_confirmation"])
    write_jsonl(paths["trajectories"], generated["canonical_trajectories"])
    write_json(paths["lineages"], {"schema_version": "actionnet-lineage-registry.v15", "records": generated["lineages"]})
    write_json(paths["reservation"], generated["protected"])
    status = "READY_FOR_CEREBRUM_DEV015_MIXED_RETENTION_REPAIR" if all(controls.values()) else "HOLD_FOR_REPAIR"
    report = {
        "schema_version": "actionnet-data-qualification-report.v15",
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
        "claim_boundary": "Mixed public training replay plus fresh project-authored synthetic checkpoint selection and confirmation only; no independent transfer, production, authority, or IGI claim.",
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
        "train_records": len(generated["datasets"]["train"]),
        "development_records": len(generated["datasets"]["development_selection"]),
        "confirmation_records": len(generated["datasets"]["untouched_confirmation"]),
    }, indent=2, sort_keys=True))
    return 0 if status.startswith("READY") else 1


if __name__ == "__main__":
    raise SystemExit(main())