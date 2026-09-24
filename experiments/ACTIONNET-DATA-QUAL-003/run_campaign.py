#!/usr/bin/env python3
"""Generate and freeze ACTIONNET-DATA-QUAL-003."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from actionnet_multiview import RESULT_ID, canonical, generate


ROOT = Path(__file__).resolve().parent
DATASET = ROOT / "dataset"
ORACLE = ROOT / "oracle"
LINEAGE = ROOT / "lineage"
RESULTS = ROOT / "results"


def sha(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(canonical(row) + "\n" for row in rows), encoding="utf-8")


def main() -> int:
    generated = generate()
    repeated = generate()
    controls = dict(generated["controls"])
    controls["byte_deterministic_generation"] = canonical(generated) == canonical(repeated)

    train_path = DATASET / "train.jsonl"
    validation_path = DATASET / "repair_validation.jsonl"
    trajectories_path = ORACLE / "canonical_trajectories.jsonl"
    lineages_path = LINEAGE / "lineages.json"
    reservation_path = ORACLE / "reservation.json"
    write_jsonl(train_path, generated["datasets"]["train"])
    write_jsonl(validation_path, generated["datasets"]["repair_validation"])
    write_jsonl(trajectories_path, generated["canonical_trajectories"])
    write_json(lineages_path, {"schema_version": "actionnet-lineage-registry.v3", "records": generated["lineages"]})
    write_json(reservation_path, generated["protected"])

    data_files = [train_path, validation_path, trajectories_path, lineages_path, reservation_path]
    dataset_manifest = {
        "schema_version": "actionnet-repair-dataset-manifest.v3",
        "dataset_id": "ACTIONNET-REPAIR-DATASET-v3.0.0",
        "parent_result": "ACTIONNET-DATA-QUAL-002-result-v1.0.0",
        "trigger_result": "CEREBRUM-DEV-001-run-2026-08-09-v1.0.0",
        "counts": {
            "train_records": len(generated["datasets"]["train"]),
            "repair_validation_records": len(generated["datasets"]["repair_validation"]),
            "canonical_trajectories": len(generated["canonical_trajectories"]),
        },
        "files": {path.relative_to(ROOT).as_posix(): sha(path) for path in data_files},
        "source_grounded": False,
        "confirmatory_ready": False,
        "public_materialized": False,
        "protected_materialized": False,
        "claim_boundary": "Fresh-lineage synthetic repair corpus for event-sensitive multi-view development only.",
    }
    write_json(RESULTS / "dataset_manifest.json", dataset_manifest)
    status = "READY_FOR_CEREBRUM_REPAIR_TRAINING" if all(controls.values()) else "HOLD_FOR_REPAIR"
    report = {
        "schema_version": "actionnet-data-qualification-report.v3",
        "result_id": RESULT_ID,
        "status": status,
        "controls": controls,
        "control_count": len(controls),
        "controls_passed": sum(controls.values()),
        "audits": generated["audits"],
        "source_grounded": False,
        "confirmatory_ready": False,
        "human_domain_review": False,
        "independent_generator_implementation": False,
        "claim_boundary": "Qualified only for a new internal Cerebrum repair campaign; no public, protected, real-institution, or production claim.",
    }
    write_json(RESULTS / "qualification_report.json", report)
    artifacts = [ROOT / "README.md", ROOT / "PREREGISTRATION.md", ROOT / "DATA_DESIGN.md", ROOT / "CEREBRUM_REPAIR_HANDOFF.md", ROOT / "actionnet_multiview.py", ROOT / "run_campaign.py", RESULTS / "dataset_manifest.json", RESULTS / "qualification_report.json", *data_files]
    manifest = {
        "schema_version": "result-manifest.v1",
        "result_id": RESULT_ID,
        "experiment_id": "ACTIONNET-DATA-QUAL-003",
        "status": status,
        "artifacts": {path.relative_to(ROOT).as_posix(): sha(path) for path in artifacts},
        "claim_boundary": report["claim_boundary"],
    }
    manifest["result_hash"] = "sha256:" + hashlib.sha256(canonical(manifest).encode("utf-8")).hexdigest()
    write_json(RESULTS / "result_manifest.json", manifest)
    checksum_paths = [*data_files, RESULTS / "dataset_manifest.json", RESULTS / "qualification_report.json", RESULTS / "result_manifest.json"]
    (RESULTS / "checksums.sha256").write_text("\n".join(f"{sha(path)[7:]}  {path.relative_to(ROOT).as_posix()}" for path in checksum_paths) + "\n", encoding="utf-8")
    print(json.dumps({
        "result_id": RESULT_ID,
        "status": status,
        "controls_passed": sum(controls.values()),
        "control_count": len(controls),
        "counts": dataset_manifest["counts"],
    }, indent=2, sort_keys=True))
    return 0 if status.startswith("READY") else 1


if __name__ == "__main__":
    raise SystemExit(main())