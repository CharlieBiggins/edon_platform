#!/usr/bin/env python3
"""Freeze and score both registered Program-001 development checkpoints."""

from __future__ import annotations

import json
import subprocess
import sys

from prepare_data import prepare
from program_common import CONFIG, ROOT, candidate_specs, read_json, sha256_path, sha256_tree, write_json


def main() -> int:
    config = read_json(CONFIG)
    prepare()
    input_path = ROOT / "prepared" / "development-selection-128.jsonl"
    base_freeze_path = ROOT / "results" / "base-development-prediction-freeze.json"
    if not base_freeze_path.is_file():
        raise SystemExit("untrained step-0 base control was not frozen before training")
    base_freeze = read_json(base_freeze_path)
    if (
        base_freeze.get("complete") is not True
        or base_freeze.get("prediction_before_training_stage") is not True
        or base_freeze.get("input_sha256") != sha256_path(input_path)
    ):
        raise SystemExit("untrained step-0 base freeze is invalid")
    base = config["base_control"]
    base_predictions = ROOT / "results" / "development-base-control-predictions.jsonl"
    subprocess.run([
        sys.executable, str(ROOT / "predict.py"),
        "--config", str(CONFIG),
        "--input", str(input_path),
        "--output", str(base_predictions),
    ], cwd=ROOT, check=True)
    base_score_path = ROOT / "results" / "development-base-control-score.json"
    subprocess.run([
        sys.executable, str(ROOT / "score.py"),
        "--input", str(input_path),
        "--predictions", str(base_predictions),
        "--output", str(base_score_path),
        "--candidate-id", base["candidate_id"],
        "--candidate-step", "0",
        "--gate", "development",
    ], cwd=ROOT, check=True)
    base_score = read_json(base_score_path)
    records = []
    for candidate in candidate_specs(config):
        adapter = candidate["adapter"]
        if not adapter.is_dir():
            raise SystemExit(f"missing candidate adapter: {adapter}")
        predictions = ROOT / "results" / f"development-{candidate['candidate_id']}-predictions.jsonl"
        subprocess.run([
            sys.executable, str(ROOT / "predict.py"),
            "--config", str(CONFIG),
            "--adapter", str(adapter),
            "--input", str(input_path),
            "--output", str(predictions),
        ], cwd=ROOT, check=True)
        score_path = ROOT / "results" / f"development-{candidate['candidate_id']}-score.json"
        subprocess.run([
            sys.executable, str(ROOT / "score.py"),
            "--input", str(input_path),
            "--predictions", str(predictions),
            "--output", str(score_path),
            "--candidate-id", candidate["candidate_id"],
            "--candidate-step", str(candidate["step"]),
            "--gate", "development",
        ], cwd=ROOT, check=True)
        score = read_json(score_path)
        records.append({
            "candidate_id": candidate["candidate_id"],
            "step": candidate["step"],
            "adapter_tree_sha256": sha256_tree(adapter),
            "predictions_sha256": sha256_path(predictions),
            "score_sha256": sha256_path(score_path),
            "count": score["examples"],
            "gate_passed": score["gate_passed"],
        })
    freeze = {
        "schema_version": "cerebrum-program-001-development-freeze.v1",
        "protocol_id": config["protocol_id"],
        "input_sha256": sha256_path(input_path),
        "base_control_freeze_sha256": sha256_path(base_freeze_path),
        "base_control": {
            "candidate_id": base["candidate_id"],
            "step": 0,
            "adapter": None,
            "predictions_sha256": sha256_path(base_predictions),
            "score_sha256": sha256_path(base_score_path),
            "count": base_score["examples"],
        },
        "candidates": records,
        "all_complete": (
            base_score["examples"] == config["development_records"]
            and all(row["count"] == config["development_records"] for row in records)
        ),
        "confirmation_accessed": False,
        "transfer_authorized": False,
        "binding_authority": False,
    }
    write_json(ROOT / "results" / "development-prediction-freeze.json", freeze)
    print(json.dumps(freeze, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())