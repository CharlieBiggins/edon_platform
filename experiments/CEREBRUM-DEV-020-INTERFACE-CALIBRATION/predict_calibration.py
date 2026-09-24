#!/usr/bin/env python3
"""Freeze the six-condition interface-calibration predictions."""

from __future__ import annotations

import json
import subprocess
import sys

from dev020_common import BASE, CONFIG, ROOT, model_adapter, read_json, sha256_path, sha256_tree, write_json
from prepare_data import prepare_calibration


def main() -> int:
    config = read_json(CONFIG)
    prepare_calibration()
    adapter = model_adapter(config)
    if not adapter.is_dir():
        raise SystemExit(f"missing frozen DEV-017 adapter: {adapter}")
    input_path = ROOT / "prepared" / "format-calibration-384.jsonl"
    output = ROOT / "results" / "calibration-predictions.jsonl"
    subprocess.run([
        sys.executable,
        str(BASE / "predict.py"),
        "--model",
        config["model_name"],
        "--config",
        str(CONFIG),
        "--adapter",
        str(adapter),
        "--input",
        str(input_path),
        "--output",
        str(output),
        "--load-in-4bit",
    ], cwd=BASE, check=True)
    base_manifest = read_json(output.with_suffix(output.suffix + ".manifest.json"))
    freeze = {
        "schema_version": "cerebrum-dev020-calibration-prediction-freeze.v1",
        "protocol_id": config["protocol_id"],
        "split": "format_calibration",
        "count": base_manifest["count"],
        "complete": base_manifest["count"] == config["registered_calibration_predictions"],
        "scenario_count": config["registered_calibration_scenarios"],
        "adapter_tree_sha256": sha256_tree(adapter),
        "input_sha256": sha256_path(input_path),
        "predictions_sha256": sha256_path(output),
        "deterministic_decoding": True,
        "training_steps": 0,
        "heldout_validation_accessed": False,
        "transfer_authorized": False,
        "binding_authority": False,
    }
    write_json(ROOT / "results" / "calibration-prediction-freeze.json", freeze)
    print(json.dumps(freeze, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
