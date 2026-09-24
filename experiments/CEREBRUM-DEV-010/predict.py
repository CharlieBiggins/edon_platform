#!/usr/bin/env python3
"""Freeze resumable predictions for one DEV-010 seed."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys

from dev010_common import BASE, CONFIG, ROOT, read_json, sha256_path, write_json
from prepare_data import prepare


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", type=int, required=True)
    args = parser.parse_args()
    config = read_json(CONFIG)
    if args.seed not in config["registered_seeds"]:
        raise SystemExit(f"seed must be one of {config['registered_seeds']}")
    prepare()
    adapter = ROOT / "artifacts" / f"dev010-seed-{args.seed}" / "final-adapter"
    training_manifest = adapter.parent / "training_manifest.json"
    if not adapter.is_dir() or not training_manifest.is_file():
        raise SystemExit(f"training incomplete for seed {args.seed}")
    predictions = ROOT / "results" / f"dev010-seed-{args.seed}-predictions.jsonl"
    subprocess.run([
        sys.executable, str(BASE / "predict.py"),
        "--model", config["model_name"],
        "--config", str(CONFIG),
        "--adapter", str(adapter),
        "--input", str(ROOT / "prepared" / "validation-192.jsonl"),
        "--output", str(predictions),
        "--load-in-4bit",
    ], cwd=BASE, check=True)
    prediction_manifest_path = predictions.with_suffix(predictions.suffix + ".manifest.json")
    prediction_manifest = read_json(prediction_manifest_path)
    prediction_manifest.update({
        "schema_version": "cerebrum-dev010-prediction-manifest.v1",
        "protocol_id": config["protocol_id"],
        "condition": config["primary_condition"],
        "seed": args.seed,
        "public_scored": False,
        "binding_authority": False,
    })
    write_json(prediction_manifest_path, prediction_manifest)
    freeze = {
        "schema_version": "cerebrum-dev010-prediction-freeze.v1",
        "protocol_id": config["protocol_id"],
        "seed": args.seed,
        "count": prediction_manifest["count"],
        "predictions_sha256": sha256_path(predictions),
        "input_sha256": sha256_path(ROOT / "prepared" / "validation-192.jsonl"),
        "training_manifest_sha256": sha256_path(training_manifest),
        "complete": prediction_manifest["count"] == 192,
        "public_scored": False,
        "binding_authority": False,
    }
    write_json(ROOT / "results" / f"dev010-seed-{args.seed}-prediction-freeze.json", freeze)
    print(json.dumps(freeze, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
