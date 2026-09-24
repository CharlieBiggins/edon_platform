#!/usr/bin/env python3
"""Freeze one untouched confirmation prediction set for the selected candidate."""

from __future__ import annotations

import json
import subprocess
import sys

from dev013_common import BASE, CONFIG, ROOT, artifact_root, candidate_specs, read_json, sha256_path, sha256_tree, write_json
from prepare_data import prepare


def main() -> int:
    config = read_json(CONFIG)
    prepare()
    selection_path = ROOT / "results" / "selected-candidate.json"
    if not selection_path.is_file():
        raise SystemExit("confirmation locked until development selection is frozen")
    selection = read_json(selection_path)
    candidate_id = selection.get("selected_candidate_id")
    if not candidate_id:
        print("No safe development candidate; untouched confirmation remains unscored.")
        return 0
    candidates = {item["candidate_id"]: item for item in candidate_specs(config)}
    candidate = candidates[candidate_id]
    adapter = candidate["adapter"]
    adapter_hash = sha256_tree(adapter)
    if adapter_hash != selection.get("selected_adapter_tree_sha256"):
        raise SystemExit("selected adapter changed after development selection")
    confirmation = ROOT / "prepared" / "untouched-confirmation-64.jsonl"
    output = ROOT / "results" / f"confirmation-{candidate_id}-predictions.jsonl"
    subprocess.run([
        sys.executable, str(BASE / "predict.py"),
        "--model", config["model_name"],
        "--config", str(CONFIG),
        "--adapter", str(adapter),
        "--input", str(confirmation),
        "--output", str(output),
        "--load-in-4bit",
    ], cwd=BASE, check=True)
    manifest_path = output.with_suffix(output.suffix + ".manifest.json")
    manifest = read_json(manifest_path)
    manifest.update({
        "schema_version": "cerebrum-dev013-confirmation-prediction-manifest.v1",
        "protocol_id": config["protocol_id"],
        "selected_candidate_id": candidate_id,
        "selected_step": candidate["step"],
        "selection_sha256": sha256_path(selection_path),
        "development_selection": False,
        "untouched_confirmation": True,
        "full_regression": False,
        "transfer_authorized": False,
        "public_scored": False,
        "binding_authority": False,
    })
    write_json(manifest_path, manifest)
    freeze = {
        "schema_version": "cerebrum-dev013-confirmation-prediction-freeze.v1",
        "protocol_id": config["protocol_id"],
        "selected_candidate_id": candidate_id,
        "selected_step": candidate["step"],
        "selection_sha256": sha256_path(selection_path),
        "adapter_tree_sha256": adapter_hash,
        "input_sha256": sha256_path(confirmation),
        "predictions_sha256": sha256_path(output),
        "training_manifest_sha256": sha256_path(artifact_root(config) / "training_manifest.json"),
        "count": manifest["count"],
        "complete": manifest["count"] == 64,
        "confirmation_single_use": True,
        "full_regression": False,
        "transfer_authorized": False,
        "binding_authority": False,
    }
    write_json(ROOT / "results" / "confirmation-prediction-freeze.json", freeze)
    print(json.dumps(freeze, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())