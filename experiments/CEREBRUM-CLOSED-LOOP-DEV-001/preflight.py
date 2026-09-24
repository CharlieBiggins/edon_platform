#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent
EXPECTED_STATUS = "READY_FOR_TWO_SEED_LEARNED_CLOSED_LOOP_DEVELOPMENT"


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def sha256_path(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def build_report() -> dict[str, Any]:
    design = read_json(ROOT / "config" / "design.json")
    manifest = read_json(ROOT / "manifest.json")
    qualification = read_json(ROOT / "results" / "qualification-report.json")
    release = read_json(ROOT / "training" / "training-release.json")
    train_episodes = read_jsonl(ROOT / "dataset" / "train-episodes.jsonl")
    train_turns = read_jsonl(ROOT / "dataset" / "train-turns.jsonl")
    validation_episodes = read_jsonl(ROOT / "dataset" / "validation-episodes.jsonl")
    validation_inputs = read_jsonl(ROOT / "dataset" / "validation-inputs.jsonl")
    validation_labels = read_jsonl(ROOT / "oracle" / "validation-labels.jsonl")
    reference_runs = read_jsonl(ROOT / "results" / "reference-runs.jsonl")
    paths = sorted(qualification["hashes"])
    checks = {
        "protocol_identity": manifest["experiment_id"] == design["protocol_id"] == qualification["protocol_id"] == "CEREBRUM-CLOSED-LOOP-DEV-001",
        "qualification_passed": qualification["status"] == EXPECTED_STATUS and qualification["control_count"] == qualification["controls_passed"],
        "train_episode_count": len(train_episodes) == 288,
        "train_turn_count": len(train_turns) == 2496,
        "validation_episode_count": len(validation_episodes) == 72,
        "validation_turn_count": len(validation_inputs) == len(validation_labels) == 624,
        "reference_run_count": len(reference_runs) == 360,
        "reference_runs_pass": all(row["episode_success"] and row["kernel_rejections"] == 0 for row in reference_runs),
        "hashes_match": all(sha256_path(ROOT / path) == qualification["hashes"][path] for path in paths),
        "manifest_artifact_hash": manifest["artifact"]["sha256"] == sha256_path(ROOT / "results" / "qualification-report.json"),
        "training_release_authorized": release["status"] == "AUTHORIZED_FOR_DEVELOPMENT_TRAINING" and release["training_authorized"] is True,
        "two_seed_registration": design["candidate_seeds"] == [26082491, 26082492],
        "validation_inputs_label_free": all("target" not in row for row in validation_inputs),
        "validation_training_prohibited": all(row["training_eligible"] is False for row in validation_inputs),
        "train_validation_profiles_disjoint": not (set(design["training_profiles"]) & set(design["heldout_validation_profiles"])),
        "train_validation_renderers_disjoint": not (set(design["training_renderers"]) & set(design["heldout_validation_renderers"])),
        "transfer008_excluded": release["transfer008_material_included"] is False,
        "capstone_excluded": release["capstone_material_included"] is False,
        "real_institution_excluded": release["real_institution_data_included"] is False,
        "kernel_only_commit": design["runtime_boundary"]["kernel_only_state_commit"] is True,
        "controller_non_binding": design["runtime_boundary"]["controller_outputs_non_binding"] is True,
        "no_binding_authority": all(row["binding_authority"] is False for row in (design, manifest, qualification, release)),
    }
    return {
        "schema_version": "cerebrum-closed-loop-dev-readiness.v1",
        "protocol_id": "CEREBRUM-CLOSED-LOOP-DEV-001",
        "status": EXPECTED_STATUS if all(checks.values()) else "CLOSED_LOOP_DEVELOPMENT_PREFLIGHT_FAILED",
        "control_count": len(checks),
        "controls_passed": sum(checks.values()),
        "controls": checks,
        "counts": qualification["counts"],
        "training_authorized": all(checks.values()),
        "learned_result_exists": False,
        "capstone_prerequisite_satisfied": False,
        "binding_authority": False,
        "claim_boundary": qualification["claim_boundary"],
    }


def main() -> int:
    report = build_report()
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["status"] == EXPECTED_STATUS else 1


if __name__ == "__main__":
    raise SystemExit(main())