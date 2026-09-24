#!/usr/bin/env python3
"""Launch or resume the registered 24-step complete-exposure continuation."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

from dev017_common import (
    CONFIG,
    PARENT,
    PREDECESSOR,
    ROOT,
    artifact_root,
    parent_adapter,
    parent_artifact_root,
    read_json,
    sha256_path,
    sha256_tree,
)
from prepare_data import prepare


def latest_checkpoint(output: Path) -> Path | None:
    checkpoints: list[tuple[int, Path]] = []
    for path in output.glob("checkpoint-*"):
        try:
            checkpoints.append((int(path.name.split("-", 1)[1]), path))
        except (IndexError, ValueError):
            continue
    return max(checkpoints, default=(0, None))[1]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--restart", action="store_true")
    args = parser.parse_args()
    config = read_json(CONFIG)
    prepare()
    adapter = parent_adapter(config)
    parent_manifest = parent_artifact_root(config) / "training_manifest.json"
    parent_predictions = PARENT / "results" / "development-continuation-step-12-predictions.jsonl"
    parent_selection = PARENT / "results" / "selected-candidate.json"
    parent_result = PARENT / "results" / "dev015-mixed-result.json"
    predecessor_selection = PREDECESSOR / "results" / "selected-candidate.json"
    predecessor_result = PREDECESSOR / "results" / "dev016-narrow-result.json"
    required = (
        adapter,
        parent_manifest,
        parent_predictions,
        parent_selection,
        parent_result,
        predecessor_selection,
        predecessor_result,
    )
    if not adapter.is_dir() or not all(path.is_file() for path in required[1:]):
        raise SystemExit("missing frozen DEV-015 step-12 parent artifacts")
    if sha256_tree(adapter) != config["parent_adapter_tree_sha256"]:
        raise SystemExit("DEV-015 step-12 adapter hash mismatch")
    if sha256_path(parent_predictions) != config["parent_development_predictions_sha256"]:
        raise SystemExit("DEV-015 step-12 development prediction hash mismatch")
    manifest = read_json(parent_manifest)
    if (
        manifest.get("protocol_id") != config["parent_protocol"]
        or manifest.get("continuation_seed") != config["parent_continuation_seed"]
        or manifest.get("config_sha256") != config["parent_config_sha256"]
    ):
        raise SystemExit("DEV-015 parent training-manifest identity mismatch")
    selection = read_json(parent_selection)
    result = read_json(parent_result)
    if selection.get("status") != config["parent_development_status"] or selection.get("selected_candidate_id") is not None:
        raise SystemExit("DEV-015 parent selection status mismatch")
    if result.get("status") != config["parent_development_status"] or result.get("confirmation_scored") is not False:
        raise SystemExit("DEV-015 parent result identity mismatch")
    prior_selection = read_json(predecessor_selection)
    prior_result = read_json(predecessor_result)
    if prior_selection.get("status") != config["predecessor_status"] or prior_selection.get("selected_candidate_id") is not None:
        raise SystemExit("DEV-016 predecessor selection identity mismatch")
    if prior_result.get("status") != config["predecessor_status"] or prior_result.get("confirmation_scored") is not False:
        raise SystemExit("DEV-016 predecessor confirmation was not sealed")

    output = artifact_root(config)
    final_manifest = output / "training_manifest.json"
    if final_manifest.is_file() and (output / "final-adapter").is_dir() and all(
        (output / f"checkpoint-{step}").is_dir() for step in (12, 24)
    ):
        print(json.dumps(read_json(final_manifest), indent=2, sort_keys=True))
        print("DEV-017 causal continuation already complete; existing checkpoints retained.")
        return 0
    command = [
        sys.executable,
        str(ROOT / "train_causal.py"),
        "--config",
        str(CONFIG),
        "--seed",
        str(config["continuation_seed"]),
        "--parent-seed",
        str(config["parent_continuation_seed"]),
        "--parent-adapter",
        str(adapter),
        "--parent-manifest",
        str(parent_manifest),
        "--train-file",
        str(ROOT / "prepared" / "train.jsonl"),
        "--validation-file",
        str(ROOT / "prepared" / "development-selection-64.jsonl"),
        "--output",
        str(output),
    ]
    checkpoint = None if args.restart else latest_checkpoint(output)
    if checkpoint is not None:
        command.extend(["--resume", str(checkpoint)])
        print(f"Resuming DEV-017 from {checkpoint}", flush=True)
    subprocess.run(command, cwd=ROOT, check=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())