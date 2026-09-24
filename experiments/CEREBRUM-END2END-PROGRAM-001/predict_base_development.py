#!/usr/bin/env python3
"""Freeze the unadapted step-0 base control before Program-001 training."""

from __future__ import annotations

import json
import subprocess
import sys

from prepare_data import prepare
from program_common import CONFIG, ROOT, artifact_root, read_json, sha256_path, write_json


def main() -> int:
    config = read_json(CONFIG)
    prepare()
    control = config["base_control"]
    input_path = ROOT / "prepared" / "development-selection-128.jsonl"
    predictions = ROOT / "results" / "development-base-control-predictions.jsonl"
    score_path = ROOT / "results" / "development-base-control-score.json"
    freeze_path = ROOT / "results" / "base-development-prediction-freeze.json"
    if freeze_path.is_file() and predictions.is_file() and score_path.is_file():
        freeze = read_json(freeze_path)
        if (
            freeze.get("complete") is True
            and freeze.get("input_sha256") == sha256_path(input_path)
            and freeze.get("predictions_sha256") == sha256_path(predictions)
            and freeze.get("score_sha256") == sha256_path(score_path)
        ):
            print(json.dumps(freeze, indent=2, sort_keys=True))
            print("Untrained step-0 development control already frozen.")
            return 0
    training_root = artifact_root(config)
    if training_root.exists() and any(training_root.iterdir()):
        raise SystemExit("training artifacts exist without a valid pre-training step-0 freeze")
    subprocess.run([
        sys.executable, str(ROOT / "predict.py"),
        "--config", str(CONFIG),
        "--input", str(input_path),
        "--output", str(predictions),
    ], cwd=ROOT, check=True)
    subprocess.run([
        sys.executable, str(ROOT / "score.py"),
        "--input", str(input_path),
        "--predictions", str(predictions),
        "--output", str(score_path),
        "--candidate-id", control["candidate_id"],
        "--candidate-step", "0",
        "--gate", "development",
    ], cwd=ROOT, check=True)
    score = read_json(score_path)
    freeze = {
        "schema_version": "cerebrum-program-001-base-development-freeze.v1",
        "protocol_id": config["protocol_id"],
        "candidate_id": control["candidate_id"],
        "candidate_step": 0,
        "adapter": None,
        "untrained_base_control": True,
        "prediction_before_training_stage": True,
        "input_sha256": sha256_path(input_path),
        "predictions_sha256": sha256_path(predictions),
        "score_sha256": sha256_path(score_path),
        "count": score["examples"],
        "complete": score["examples"] == config["development_records"],
        "transfer_authorized": False,
        "binding_authority": False,
    }
    write_json(freeze_path, freeze)
    print(json.dumps(freeze, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())