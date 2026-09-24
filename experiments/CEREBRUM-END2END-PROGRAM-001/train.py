#!/usr/bin/env python3
"""Launch or resume the registered Program-001 fresh-adapter training."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

from prepare_data import prepare
from program_common import CONFIG, ROOT, artifact_root, read_json


def latest_checkpoint(output: Path) -> Path | None:
    checkpoints = []
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
    output = artifact_root(config)
    manifest = output / "training_manifest.json"
    if manifest.is_file() and all((output / f"checkpoint-{step}").is_dir() for step in (64, 128)):
        print(json.dumps(read_json(manifest), indent=2, sort_keys=True))
        print("Program-001 training already complete; registered checkpoints retained.")
        return 0
    command = [
        sys.executable,
        str(ROOT / "train_program.py"),
        "--config", str(CONFIG),
        "--train-file", str(ROOT / "prepared" / "train-1024.jsonl"),
        "--validation-file", str(ROOT / "prepared" / "development-selection-128.jsonl"),
        "--output", str(output),
    ]
    checkpoint = None if args.restart else latest_checkpoint(output)
    if checkpoint is not None:
        command.extend(["--resume", str(checkpoint)])
        print(f"Resuming Program-001 from {checkpoint}", flush=True)
    subprocess.run(command, cwd=ROOT, check=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())