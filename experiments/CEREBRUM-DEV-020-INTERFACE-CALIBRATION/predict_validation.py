#!/usr/bin/env python3
"""Freeze raw, selected-interface, and decision-fidelity heldout predictions."""

from __future__ import annotations

import json
import subprocess
import sys

from dev020_common import BASE, CONFIG, ROOT, model_adapter, read_json, sha256_path, sha256_tree, write_json
from prepare_data import prepare_validation


def main() -> int:
    config = read_json(CONFIG)
    selection_path = ROOT / "results" / "representation-selection-freeze.json"
    if not selection_path.is_file():
        raise SystemExit("heldout validation locked until representation selection is frozen")
    selection = read_json(selection_path)
    selected = selection.get("selected_representation")
    if not selected or selection.get("representation_qualified") is not True:
        raise SystemExit("no representation qualified; heldout validation remains sealed")
    manifest = prepare_validation(selected)
    if manifest["records"] != config["registered_heldout_predictions_after_selection"]:
        raise SystemExit("heldout validation record count mismatch")
    adapter = model_adapter(config)
    if not adapter.is_dir():
        raise SystemExit(f"missing frozen DEV-017 adapter: {adapter}")
    input_path = ROOT / "prepared" / "heldout-selected-validation-192.jsonl"
    output = ROOT / "results" / "validation-predictions.jsonl"
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
        "schema_version": "cerebrum-dev020-validation-prediction-freeze.v1",
        "protocol_id": config["protocol_id"],
        "split": "heldout_format_validation",
        "selected_representation": selected,
        "count": base_manifest["count"],
        "complete": base_manifest["count"] == config["registered_heldout_predictions_after_selection"],
        "scenario_count": config["registered_heldout_scenarios"],
        "adapter_tree_sha256": sha256_tree(adapter),
        "input_sha256": sha256_path(input_path),
        "predictions_sha256": sha256_path(output),
        "selection_freeze_sha256": sha256_path(selection_path),
        "deterministic_decoding": True,
        "training_steps": 0,
        "heldout_validation_accessed": True,
        "transfer_authorized": False,
        "binding_authority": False,
    }
    write_json(ROOT / "results" / "validation-prediction-freeze.json", freeze)
    print(json.dumps(freeze, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
