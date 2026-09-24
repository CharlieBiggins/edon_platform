#!/usr/bin/env python3
"""Launch or resume the registered 24-step balance continuation."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

from dev012_common import CONFIG, CONTINUATION_TRAINER, PARENT, ROOT, read_json, sha256_path, write_json
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
    parent_continuation_seed = int(config["parent_continuation_seed"])
    parent_dev010_seed = int(config["parent_dev010_seed"])
    parent_root = PARENT / "artifacts" / f"dev011-parent-{parent_dev010_seed}-seed-{parent_continuation_seed}"
    parent_adapter = parent_root / "final-adapter"
    parent_manifest = parent_root / "training_manifest.json"
    if not parent_adapter.is_dir() or not parent_manifest.is_file():
        raise SystemExit(f"missing DEV-011 parent artifacts: {parent_root}")
    actual_hash = sha256_path(parent_manifest)
    if actual_hash != config["parent_training_manifest_sha256"]:
        raise SystemExit(
            f"parent manifest hash mismatch: {actual_hash} != {config['parent_training_manifest_sha256']}"
        )
    parent_data = read_json(parent_manifest)
    if (
        parent_data.get("protocol_id") != "CEREBRUM-DEV-011-FOCUSED"
        or int(parent_data.get("continuation_seed", -1)) != parent_continuation_seed
    ):
        raise SystemExit("DEV-011 parent training manifest identity mismatch")
    seed = int(config["continuation_seed"])
    output = ROOT / "artifacts" / f"dev012-parent-{parent_continuation_seed}-seed-{seed}"
    final_manifest = output / "training_manifest.json"
    if final_manifest.is_file() and (output / "final-adapter").is_dir():
        print(final_manifest.read_text(encoding="utf-8"), end="")
        print("DEV-012 balance continuation already complete; existing adapter retained.")
        return 0
    command = [
        sys.executable, str(CONTINUATION_TRAINER),
        "--config", str(CONFIG),
        "--seed", str(seed),
        "--parent-seed", str(parent_continuation_seed),
        "--parent-adapter", str(parent_adapter),
        "--parent-manifest", str(parent_manifest),
        "--train-file", str(ROOT / "prepared" / "train.jsonl"),
        "--validation-file", str(ROOT / "prepared" / "focused-validation-64.jsonl"),
        "--output", str(output),
    ]
    checkpoint = None if args.restart else latest_checkpoint(output)
    if checkpoint is not None:
        command.extend(["--resume", str(checkpoint)])
        print(f"Resuming DEV-012 from {checkpoint}", flush=True)
    subprocess.run(command, cwd=PARENT, check=True)
    manifest = read_json(final_manifest)
    manifest.update({
        "schema_version": "cerebrum-dev012-focused-training-manifest.v1",
        "protocol_id": config["protocol_id"],
        "source_dataset": config["source_dataset"],
        "parent_protocol": config["parent_protocol"],
        "parent_continuation_seed": parent_continuation_seed,
        "parent_dev010_seed": parent_dev010_seed,
        "adaptive_parent_failure": "CEREBRUM-DEV-011-FOCUSED resolved-ALLOW floor 30/32",
        "full_regression": False,
        "transfer_authorized": False,
        "claim_boundary": "Short balanced synthetic appeal-finality continuation only; no full regression, transfer, production, authority, or IGI claim.",
    })
    write_json(final_manifest, manifest)
    print(json.dumps(manifest, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())