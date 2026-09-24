#!/usr/bin/env python3
"""Freeze resumable predictions for the DEV-012 balance continuation."""

from __future__ import annotations

import json
import subprocess
import sys

from dev012_common import BASE, CONFIG, ROOT, read_json, sha256_path, write_json
from prepare_data import prepare


def main() -> int:
    config = read_json(CONFIG)
    prepare()
    seed = int(config["continuation_seed"])
    parent_seed = int(config["parent_continuation_seed"])
    artifact = ROOT / "artifacts" / f"dev012-parent-{parent_seed}-seed-{seed}"
    adapter = artifact / "final-adapter"
    training_manifest = artifact / "training_manifest.json"
    if not adapter.is_dir() or not training_manifest.is_file():
        raise SystemExit("DEV-012 training is incomplete")
    predictions = ROOT / "results" / f"dev012-seed-{seed}-predictions.jsonl"
    subprocess.run([
        sys.executable, str(BASE / "predict.py"),
        "--model", config["model_name"],
        "--config", str(CONFIG),
        "--adapter", str(adapter),
        "--input", str(ROOT / "prepared" / "focused-validation-64.jsonl"),
        "--output", str(predictions),
        "--load-in-4bit",
    ], cwd=BASE, check=True)
    prediction_manifest_path = predictions.with_suffix(predictions.suffix + ".manifest.json")
    prediction_manifest = read_json(prediction_manifest_path)
    prediction_manifest.update({
        "schema_version": "cerebrum-dev012-focused-prediction-manifest.v1",
        "protocol_id": config["protocol_id"],
        "condition": config["primary_condition"],
        "continuation_seed": seed,
        "parent_continuation_seed": parent_seed,
        "full_regression": False,
        "transfer_authorized": False,
        "public_scored": False,
        "binding_authority": False,
    })
    write_json(prediction_manifest_path, prediction_manifest)
    freeze = {
        "schema_version": "cerebrum-dev012-focused-prediction-freeze.v1",
        "protocol_id": config["protocol_id"],
        "continuation_seed": seed,
        "parent_continuation_seed": parent_seed,
        "count": prediction_manifest["count"],
        "predictions_sha256": sha256_path(predictions),
        "input_sha256": sha256_path(ROOT / "prepared" / "focused-validation-64.jsonl"),
        "training_manifest_sha256": sha256_path(training_manifest),
        "complete": prediction_manifest["count"] == 64,
        "full_regression": False,
        "transfer_authorized": False,
        "public_scored": False,
        "binding_authority": False,
    }
    write_json(ROOT / "results" / f"dev012-seed-{seed}-prediction-freeze.json", freeze)
    print(json.dumps(freeze, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())