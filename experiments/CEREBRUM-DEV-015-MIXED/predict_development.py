#!/usr/bin/env python3
"""Freeze development predictions for four mixed-repair checkpoints."""

from __future__ import annotations

import json
import subprocess
import sys

from dev015_common import BASE, CONFIG, ROOT, candidate_specs, read_json, sha256_path, sha256_tree, write_json
from prepare_data import prepare


def main() -> int:
    config = read_json(CONFIG)
    prepare()
    development = ROOT / "prepared" / "development-selection-64.jsonl"
    records = []
    for candidate in candidate_specs(config):
        adapter = candidate["adapter"]
        if not adapter.is_dir():
            raise SystemExit(f"missing registered candidate adapter: {adapter}")
        output = ROOT / "results" / f"development-{candidate['candidate_id']}-predictions.jsonl"
        subprocess.run([
            sys.executable, str(BASE / "predict.py"),
            "--model", config["model_name"],
            "--config", str(CONFIG),
            "--adapter", str(adapter),
            "--input", str(development),
            "--output", str(output),
            "--load-in-4bit",
        ], cwd=BASE, check=True)
        manifest_path = output.with_suffix(output.suffix + ".manifest.json")
        manifest = read_json(manifest_path)
        manifest.update({
            "schema_version": "cerebrum-dev015-development-prediction-manifest.v1",
            "protocol_id": config["protocol_id"],
            "candidate_id": candidate["candidate_id"],
            "candidate_step": candidate["step"],
            "development_selection": True,
            "confirmation": False,
            "full_regression": False,
            "transfer_authorized": False,
            "public_scored": False,
            "binding_authority": False,
        })
        write_json(manifest_path, manifest)
        records.append({
            "candidate_id": candidate["candidate_id"],
            "step": candidate["step"],
            "adapter_tree_sha256": sha256_tree(adapter),
            "predictions_sha256": sha256_path(output),
            "count": manifest["count"],
            "complete": manifest["count"] == 64,
        })
    freeze = {
        "schema_version": "cerebrum-dev015-development-prediction-freeze.v1",
        "protocol_id": config["protocol_id"],
        "input_sha256": sha256_path(development),
        "candidates": records,
        "all_complete": all(item["complete"] for item in records),
        "development_selection": True,
        "confirmation": False,
        "full_regression": False,
        "transfer_authorized": False,
        "binding_authority": False,
    }
    write_json(ROOT / "results" / "development-prediction-freeze.json", freeze)
    print(json.dumps(freeze, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())