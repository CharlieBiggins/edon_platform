#!/usr/bin/env python3
"""Launch or resume the registered 24-step mixed continuation."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

from dev015_common import CONFIG, PARENT, ROOT, artifact_root, parent_adapter, parent_artifact_root, read_json, sha256_path
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
    selection_path = PARENT / "results" / "selected-candidate.json"
    if not adapter.is_dir() or not parent_manifest.is_file() or not selection_path.is_file():
        raise SystemExit("missing frozen DEV-013 selected-parent artifacts")
    if sha256_path(parent_manifest) != config["parent_training_manifest_sha256"]:
        raise SystemExit("DEV-013 parent training-manifest hash mismatch")
    if sha256_path(selection_path) != config["parent_selection_sha256"]:
        raise SystemExit("DEV-013 parent selection hash mismatch")
    selection = read_json(selection_path)
    if selection.get("selected_candidate_id") != config["parent_selected_candidate_id"] or selection.get("selected_step") != config["parent_selected_step"]:
        raise SystemExit("DEV-013 selected-parent identity mismatch")
    output = artifact_root(config)
    final_manifest = output / "training_manifest.json"
    if final_manifest.is_file() and (output / "final-adapter").is_dir() and all((output / f"checkpoint-{step}").is_dir() for step in (12, 24)):
        print(json.dumps(read_json(final_manifest), indent=2, sort_keys=True))
        print("DEV-015 mixed continuation already complete; existing checkpoints retained.")
        return 0
    command = [
        sys.executable, str(ROOT / "train_mixed.py"),
        "--config", str(CONFIG),
        "--seed", str(config["continuation_seed"]),
        "--parent-seed", str(config["parent_continuation_seed"]),
        "--parent-adapter", str(adapter),
        "--parent-manifest", str(parent_manifest),
        "--train-file", str(ROOT / "prepared" / "train.jsonl"),
        "--validation-file", str(ROOT / "prepared" / "development-selection-64.jsonl"),
        "--output", str(output),
    ]
    checkpoint = None if args.restart else latest_checkpoint(output)
    if checkpoint is not None:
        command.extend(["--resume", str(checkpoint)])
        print(f"Resuming DEV-015 from {checkpoint}", flush=True)
    subprocess.run(command, cwd=ROOT, check=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())