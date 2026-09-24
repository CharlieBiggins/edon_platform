#!/usr/bin/env python3
"""Generate and freeze ACTIONNET-DATA-QUAL-009."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from actionnet_multigen import (
    DATASET_ID,
    PIVOTAL_MECHANISMS,
    PROTOCOL_ID,
    RESULT_ID,
    canonical,
    generate,
)


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
    mechanism_path = ORACLE / "mechanism_catalog.json"
    overlap_path = ORACLE / "actionnet007_overlap_reference.json"
    write_jsonl(train_path, generated["datasets"]["train"])
    write_jsonl(validation_path, generated["datasets"]["repair_validation"])
    write_jsonl(trajectories_path, generated["canonical_trajectories"])
    write_json(lineages_path, {"schema_version": "actionnet-lineage-registry.v9", "records": generated["lineages"]})
    write_json(reservation_path, generated["protected"])
    write_json(mechanism_path, {
        "schema_version": "actionnet-event-mechanism-catalog.v1",
        "protocol_id": PROTOCOL_ID,
        "pivotal_mechanisms": list(PIVOTAL_MECHANISMS),
        "invariance_mechanism": "QUEUE_ORDER_AND_ACTOR_RENAME",
        "contextual_mechanism": "DECISIVE_CONTEXT_PRESERVATION",
        "scheduler_order": ["time", "priority", "sequence", "event_id"],
        "events_after_disposition_time": "deferred",
        "binding_authority": False,
    })

    data_files = [train_path, validation_path, trajectories_path, lineages_path, reservation_path, mechanism_path, overlap_path]
    dataset_manifest = {
        "schema_version": "actionnet-eventnet-dataset-manifest.v9",
        "dataset_id": DATASET_ID,
        "parent_result": "ACTIONNET-DATA-QUAL-007-result-v1.0.0",
        "counts": {
            "train_records": len(generated["datasets"]["train"]),
            "repair_validation_records": len(generated["datasets"]["repair_validation"]),
            "canonical_trajectories": len(generated["canonical_trajectories"]),
            "counterfactual_pairs": len(generated["counterfactual_pairs"]),
        },
        "task_types": ["CERTIFICATE", "TRANSITION", "QUEUE_TRACE", "PAIR_CONTRAST"],
        "training_generator_profiles": generated["audits"]["train_generator_profiles"],
        "heldout_validation_generator_profiles": generated["audits"]["repair_validation_generator_profiles"],
        "files": {path.relative_to(ROOT).as_posix(): sha(path) for path in data_files},
        "source_grounded": False,
        "human_domain_review": False,
        "confirmatory_ready": False,
        "public_materialized": False,
        "protected_materialized": False,
        "claim_boundary": "Fresh-lineage, project-authored multi-generator synthetic repair corpus for internal EventNet learning only.",
    }
    write_json(RESULTS / "dataset_manifest.json", dataset_manifest)
    status = "READY_FOR_CEREBRUM_EVENTNET_DEVELOPMENT" if all(controls.values()) else "HOLD_FOR_REPAIR"
    report = {
        "schema_version": "actionnet-data-qualification-report.v9",
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
        "project_authored_generator_profiles": ["LEDGER", "MATRIX", "GRAPH"],
        "binding_authority": False,
        "claim_boundary": "Qualified for the separate CEREBRUM-DEV-009 multi-generator repair campaign; generator profiles remain project-authored and no public, protected, real-institution, autonomous-authority, or production claim is made.",
    }
    write_json(RESULTS / "qualification_report.json", report)

    documentation = [
        ROOT / "README.md",
        ROOT / "PREREGISTRATION.md",
        ROOT / "DATA_DESIGN.md",
        ROOT / "SCALING_ARCHITECTURE.md",
        ROOT / "CEREBRUM_EVENTNET_HANDOFF.md",
    ]
    implementation = [ROOT / "actionnet_multigen.py", ROOT / "freeze_predecessor_overlap.py", ROOT / "run_campaign.py", ROOT / "tests" / "test_eventnet.py"]
    artifacts = [*documentation, *implementation, RESULTS / "dataset_manifest.json", RESULTS / "qualification_report.json", *data_files]
    manifest = {
        "schema_version": "result-manifest.v1",
        "result_id": RESULT_ID,
        "experiment_id": PROTOCOL_ID,
        "status": status,
        "artifacts": {path.relative_to(ROOT).as_posix(): sha(path) for path in artifacts},
        "claim_boundary": report["claim_boundary"],
    }
    manifest["result_hash"] = "sha256:" + hashlib.sha256(canonical(manifest).encode("utf-8")).hexdigest()
    write_json(RESULTS / "result_manifest.json", manifest)
    checksum_paths = [*data_files, RESULTS / "dataset_manifest.json", RESULTS / "qualification_report.json", RESULTS / "result_manifest.json"]
    (RESULTS / "checksums.sha256").write_text(
        "\n".join(f"{sha(path)[7:]}  {path.relative_to(ROOT).as_posix()}" for path in checksum_paths) + "\n",
        encoding="utf-8",
    )
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