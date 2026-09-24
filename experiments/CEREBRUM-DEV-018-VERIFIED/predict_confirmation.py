#!/usr/bin/env python3
"""Predict confirmation only after a frozen verified-hybrid development pass."""

from __future__ import annotations

import json
import subprocess
import sys

from dev018_common import BASE, CONFIG, ROOT, model_adapter, read_json, sha256_path, sha256_tree, write_json
from prepare_data import prepare


def main() -> int:
    config = read_json(CONFIG)
    prepare()
    development_result_path = ROOT / "results" / "development-result.json"
    if not development_result_path.is_file():
        raise SystemExit("confirmation locked until development result exists")
    development_result = read_json(development_result_path)
    if development_result.get("status") != "VERIFIED_HYBRID_DEVELOPMENT_PASS":
        print("Verified hybrid did not pass development; confirmation remains sealed.")
        return 0
    adapter = model_adapter(config)
    if sha256_tree(adapter) != config["model_parent_adapter_tree_sha256"]:
        raise SystemExit("frozen model adapter changed before confirmation")
    input_path = ROOT / "prepared" / "untouched-confirmation-192.jsonl"
    output = ROOT / "results" / "confirmation-model-predictions.jsonl"
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
        "split": "confirmation",
        "model_only": True,
        "development_result_sha256": sha256_path(development_result_path),
        "confirmation_single_use": True,
        "transfer_authorized": False,
        "binding_authority": False,
    })
    write_json(manifest_path, manifest)
    freeze = {
        "schema_version": "cerebrum-dev018-model-prediction-freeze.v1",
        "protocol_id": config["protocol_id"],
        "split": "confirmation",
        "count": manifest["count"],
        "complete": manifest["count"] == 192,
        "development_result_sha256": sha256_path(development_result_path),
        "adapter_tree_sha256": sha256_tree(adapter),
        "input_sha256": sha256_path(input_path),
        "predictions_sha256": sha256_path(output),
        "confirmation_single_use": True,
        "binding_authority": False,
        "transfer_authorized": False,
    }
    write_json(ROOT / "results" / "confirmation-model-prediction-freeze.json", freeze)
    print(json.dumps(freeze, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())