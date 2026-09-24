#!/usr/bin/env python3
"""Freeze all five diagnostic conditions from the unchanged model."""

from __future__ import annotations

import json
import subprocess
import sys

from dev019_common import BASE, CONFIG, ROOT, model_adapter, read_json, sha256_path, sha256_tree, write_json
from prepare_data import prepare


def main() -> int:
    config = read_json(CONFIG)
    prepare()
    adapter = model_adapter(config)
    if not adapter.is_dir():
        raise SystemExit(f"missing frozen DEV-017 adapter: {adapter}")
    input_path = ROOT / "prepared" / "diagnostic-matrix-160.jsonl"
    output = ROOT / "results" / "diagnostic-predictions.jsonl"
    subprocess.run([
        sys.executable, str(BASE / "predict.py"),
        "--model", config["model_name"],
        "--config", str(CONFIG),
        "--adapter", str(adapter),
        "--input", str(input_path),
        "--output", str(output),
        "--load-in-4bit",
    ], cwd=BASE, check=True)
    base_manifest_path = output.with_suffix(output.suffix + ".manifest.json")
    base_manifest = read_json(base_manifest_path)
    freeze = {
        "schema_version": "cerebrum-dev019-diagnostic-prediction-freeze.v1",
        "protocol_id": config["protocol_id"],
        "count": base_manifest["count"],
        "complete": base_manifest["count"] == config["registered_predictions"],
        "scenario_count": config["registered_scenarios"],
        "conditions": config["diagnostic_conditions"],
        "adapter_tree_sha256": sha256_tree(adapter),
        "input_sha256": sha256_path(input_path),
        "predictions_sha256": sha256_path(output),
        "deterministic_decoding": True,
        "training_steps": 0,
        "confirmation": False,
        "transfer_authorized": False,
        "binding_authority": False,
    }
    write_json(ROOT / "results" / "diagnostic-prediction-freeze.json", freeze)
    print(json.dumps(freeze, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())