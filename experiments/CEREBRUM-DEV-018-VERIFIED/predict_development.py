#!/usr/bin/env python3
"""Freeze model-only predictions for fresh development cases."""

from __future__ import annotations

import json
import subprocess
import sys

from dev018_common import BASE, CONFIG, ROOT, model_adapter, read_json, sha256_path, sha256_tree, write_json
from prepare_data import prepare


def main() -> int:
    config = read_json(CONFIG)
    prepare()
    adapter = model_adapter(config)
    if not adapter.is_dir():
        raise SystemExit(f"missing frozen DEV-017 engineering adapter: {adapter}")
    input_path = ROOT / "prepared" / "development-selection-64.jsonl"
    output = ROOT / "results" / "development-model-predictions.jsonl"
    subprocess.run([
        sys.executable, str(BASE / "predict.py"),
        "--model", config["model_name"],
        "--config", str(CONFIG),
        "--adapter", str(adapter),
        "--input", str(input_path),
        "--output", str(output),
        "--load-in-4bit",
    ], cwd=BASE, check=True)
    manifest_path = output.with_suffix(output.suffix + ".manifest.json")
    manifest = read_json(manifest_path)
    manifest.update({
        "schema_version": "cerebrum-dev018-model-prediction-manifest.v1",
        "protocol_id": config["protocol_id"],
        "split": "development",
        "model_only": True,
        "engineering_parent_not_scientifically_promoted": True,
        "confirmation": False,
        "transfer_authorized": False,
        "binding_authority": False,
    })
    write_json(manifest_path, manifest)
    freeze = {
        "schema_version": "cerebrum-dev018-model-prediction-freeze.v1",
        "protocol_id": config["protocol_id"],
        "split": "development",
        "count": manifest["count"],
        "complete": manifest["count"] == 64,
        "adapter_tree_sha256": sha256_tree(adapter),
        "input_sha256": sha256_path(input_path),
        "predictions_sha256": sha256_path(output),
        "confirmation": False,
        "binding_authority": False,
        "transfer_authorized": False,
    }
    write_json(ROOT / "results" / "development-model-prediction-freeze.json", freeze)
    print(json.dumps(freeze, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())