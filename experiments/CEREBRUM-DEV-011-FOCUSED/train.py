#!/usr/bin/env python3
"""Launch or resume one registered focused continuation run."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

from dev011_common import CONFIG, PARENT, ROOT, read_json, run_spec, sha256_path
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
    parser.add_argument("--seed", type=int, required=True, help="Registered continuation seed")
    parser.add_argument("--restart", action="store_true")
    args = parser.parse_args()
    config = read_json(CONFIG)
    try:
        spec = run_spec(config, args.seed)
    except ValueError as error:
        raise SystemExit(str(error)) from error
    prepare()
    parent_seed = int(spec["parent_seed"])
    parent_root = PARENT / "artifacts" / f"dev010-seed-{parent_seed}"
    parent_adapter = parent_root / "final-adapter"
    parent_manifest = parent_root / "training_manifest.json"
    if not parent_adapter.is_dir() or not parent_manifest.is_file():
        raise SystemExit(f"missing frozen DEV-010 parent artifacts for seed {parent_seed}: {parent_root}")
    actual_hash = sha256_path(parent_manifest)
    if actual_hash != spec["parent_training_manifest_sha256"]:
        raise SystemExit(
            f"parent manifest hash mismatch for seed {parent_seed}: {actual_hash} != {spec['parent_training_manifest_sha256']}"
        )
    parent_data = read_json(parent_manifest)
    if parent_data.get("protocol_id") != "CEREBRUM-DEV-010" or int(parent_data.get("seed", -1)) != parent_seed:
        raise SystemExit("parent training manifest identity mismatch")
    output = ROOT / "artifacts" / f"dev011-parent-{parent_seed}-seed-{args.seed}"
    final_manifest = output / "training_manifest.json"
    if final_manifest.is_file() and (output / "final-adapter").is_dir():
        print(final_manifest.read_text(encoding="utf-8"), end="")
        print("Focused continuation already complete; existing adapter retained.")
        return 0
    command = [
        sys.executable, str(ROOT / "train_continuation.py"),
        "--config", str(CONFIG),
        "--seed", str(args.seed),
        "--parent-seed", str(parent_seed),
        "--parent-adapter", str(parent_adapter),
        "--parent-manifest", str(parent_manifest),
        "--train-file", str(ROOT / "prepared" / "train.jsonl"),
        "--validation-file", str(ROOT / "prepared" / "focused-validation-64.jsonl"),
        "--output", str(output),
    ]
    checkpoint = None if args.restart else latest_checkpoint(output)
    if checkpoint is not None:
        command.extend(["--resume", str(checkpoint)])
        print(f"Resuming continuation seed {args.seed} from {checkpoint}", flush=True)
    subprocess.run(command, cwd=ROOT, check=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())