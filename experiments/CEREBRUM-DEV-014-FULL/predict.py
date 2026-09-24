#!/usr/bin/env python3
"""Freeze the selected DEV-013 candidate on the full regression."""

from __future__ import annotations

import json
import subprocess
import sys

from dev014_common import BASE, CONFIG, PARENT, ROOT, parent_artifact_root, read_json, selected_adapter, sha256_path, sha256_tree, write_json
from prepare_data import prepare


def main() -> int:
    config = read_json(CONFIG)
    prepare()
    selection_path = PARENT / "results" / "selected-candidate.json"
    result_path = PARENT / "results" / "dev013-focused-result.json"
    training_manifest = parent_artifact_root(config) / "training_manifest.json"
    adapter = selected_adapter(config)
    for path in (selection_path, result_path, training_manifest):
        if not path.is_file():
            raise SystemExit(f"missing frozen DEV-013 parent artifact: {path}")
    if not adapter.is_dir():
        raise SystemExit(f"missing selected DEV-013 adapter: {adapter}")
    selection = read_json(selection_path)
    parent_result = read_json(result_path)
    checks = {
        "selection_hash": sha256_path(selection_path) == config["parent_selection_sha256"],
        "candidate_identity": selection.get("selected_candidate_id") == config["selected_candidate_id"] and selection.get("selected_step") == config["selected_step"],
        "adapter_hash": sha256_tree(adapter) == config["selected_adapter_tree_sha256"],
        "training_manifest_hash": sha256_path(training_manifest) == config["parent_training_manifest_sha256"],
        "confirmation_passed": parent_result.get("passed") is True and parent_result.get("status") == "FOCUSED_NEAR_CLOCK_REPAIR_SIGNAL",
        "confirmation_candidate": parent_result.get("selected_candidate_id") == config["selected_candidate_id"],
        "confirmation_input_hash": parent_result.get("confirmation_input_sha256") == config["parent_confirmation_input_sha256"],
        "confirmation_predictions_hash": parent_result.get("confirmation_predictions_sha256") == config["parent_confirmation_predictions_sha256"],
    }
    if not all(checks.values()):
        raise SystemExit("DEV-013 parent identity failed: " + json.dumps(checks, sort_keys=True))
    source = ROOT / "prepared" / "full-regression-192.jsonl"
    output = ROOT / "results" / "dev014-full-predictions.jsonl"
    subprocess.run([
        sys.executable, str(BASE / "predict.py"),
        "--model", config["model_name"],
        "--config", str(CONFIG),
        "--adapter", str(adapter),
        "--input", str(source),
        "--output", str(output),
        "--load-in-4bit",
    ], cwd=BASE, check=True)
    manifest_path = output.with_suffix(output.suffix + ".manifest.json")
    manifest = read_json(manifest_path)
    manifest.update({
        "schema_version": "cerebrum-dev014-full-prediction-manifest.v1",
        "protocol_id": config["protocol_id"],
        "selected_candidate_id": config["selected_candidate_id"],
        "selected_step": config["selected_step"],
        "parent_selection_sha256": config["parent_selection_sha256"],
        "full_regression": True,
        "transfer_authorized": False,
        "public_scored": False,
        "binding_authority": False,
    })
    write_json(manifest_path, manifest)
    freeze = {
        "schema_version": "cerebrum-dev014-full-prediction-freeze.v1",
        "protocol_id": config["protocol_id"],
        "selected_candidate_id": config["selected_candidate_id"],
        "selected_step": config["selected_step"],
        "adapter_tree_sha256": sha256_tree(adapter),
        "training_manifest_sha256": sha256_path(training_manifest),
        "parent_selection_sha256": sha256_path(selection_path),
        "input_sha256": sha256_path(source),
        "predictions_sha256": sha256_path(output),
        "count": manifest["count"],
        "complete": manifest["count"] == 192,
        "full_regression": True,
        "transfer_authorized": False,
        "binding_authority": False,
    }
    write_json(ROOT / "results" / "dev014-full-prediction-freeze.json", freeze)
    print(json.dumps(freeze, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())