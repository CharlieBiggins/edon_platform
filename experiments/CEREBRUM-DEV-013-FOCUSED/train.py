#!/usr/bin/env python3
"""Launch or resume the registered 12-step near-clock continuation."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

from dev013_common import CONFIG, CONTINUATION_TRAINER, PARENT, ROOT, artifact_root, parent_root, read_json, sha256_path, write_json
from prepare_data import prepare


def latest_checkpoint(output: Path) -> Path | None:
    checkpoints: list[tuple[int, Path]] = []
    for path in output.glob("checkpoint-*"):
        try:
            checkpoints.append((int(path.name.split("-", 1)[1]), path))
        except (IndexError, ValueError):
            continue
    return max(checkpoints, default=(0, None))[1]


def finalize_manifest(manifest: dict, config: dict) -> dict:
    manifest.update({
        "schema_version": "cerebrum-dev013-focused-training-manifest.v1",
        "protocol_id": config["protocol_id"],
        "source_dataset": config["source_dataset"],
        "parent_protocol": config["parent_protocol"],
        "parent_continuation_seed": config["parent_continuation_seed"],
        "parent_checkpoint_step": config["parent_checkpoint_step"],
        "adaptive_parent_result": "DEV-012 same-instrument safe checkpoint-12",
        "development_selection": True,
        "confirmation_single_use": True,
        "full_regression": False,
        "transfer_authorized": False,
        "claim_boundary": "Short synthetic near-clock continuation and development selection only; no confirmation result, full regression, transfer, production, authority, or IGI claim.",
    })
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--restart", action="store_true")
    args = parser.parse_args()
    config = read_json(CONFIG)
    prepare()
    parent = parent_root(config)
    parent_adapter = parent / f"checkpoint-{config['parent_checkpoint_step']}"
    parent_manifest = parent / "training_manifest.json"
    if not parent_adapter.is_dir() or not parent_manifest.is_file():
        raise SystemExit(f"missing DEV-012 checkpoint-12 parent artifacts: {parent}")
    actual_hash = sha256_path(parent_manifest)
    if actual_hash != config["parent_training_manifest_sha256"]:
        raise SystemExit(f"parent manifest hash mismatch: {actual_hash} != {config['parent_training_manifest_sha256']}")
    parent_data = read_json(parent_manifest)
    if (
        parent_data.get("protocol_id") != "CEREBRUM-DEV-012-FOCUSED"
        or int(parent_data.get("continuation_seed", -1)) != int(config["parent_continuation_seed"])
    ):
        raise SystemExit("DEV-012 parent training manifest identity mismatch")
    output = artifact_root(config)
    final_manifest = output / "training_manifest.json"
    if final_manifest.is_file() and (output / "final-adapter").is_dir():
        manifest = finalize_manifest(read_json(final_manifest), config)
        write_json(final_manifest, manifest)
        print(json.dumps(manifest, indent=2, sort_keys=True))
        print("DEV-013 near-clock continuation already complete; existing adapter retained.")
        return 0
    command = [
        sys.executable, str(CONTINUATION_TRAINER),
        "--config", str(CONFIG),
        "--seed", str(config["continuation_seed"]),
        "--parent-seed", str(config["parent_continuation_seed"]),
        "--parent-adapter", str(parent_adapter),
        "--parent-manifest", str(parent_manifest),
        "--train-file", str(ROOT / "prepared" / "train.jsonl"),
        "--validation-file", str(ROOT / "prepared" / "development-selection-32.jsonl"),
        "--output", str(output),
    ]
    checkpoint = None if args.restart else latest_checkpoint(output)
    if checkpoint is not None:
        command.extend(["--resume", str(checkpoint)])
        print(f"Resuming DEV-013 from {checkpoint}", flush=True)
    subprocess.run(command, cwd=PARENT, check=True)
    manifest = finalize_manifest(read_json(final_manifest), config)
    write_json(final_manifest, manifest)
    print(json.dumps(manifest, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())