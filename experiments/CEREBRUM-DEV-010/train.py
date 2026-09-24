#!/usr/bin/env python3
"""Train one registered DEV-010 seed with checkpoint resume."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

from dev010_common import BASE, CONFIG, ROOT, read_json, write_json
from prepare_data import prepare


def latest_checkpoint(output: Path) -> Path | None:
    values = []
    for path in output.glob("checkpoint-*"):
        try:
            values.append((int(path.name.split("-", 1)[1]), path))
        except (IndexError, ValueError):
            continue
    return max(values, default=(0, None))[1]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument("--restart", action="store_true")
    args = parser.parse_args()
    config = read_json(CONFIG)
    if args.seed not in config["registered_seeds"]:
        raise SystemExit(f"seed must be one of {config['registered_seeds']}")
    prepare()
    output = ROOT / "artifacts" / f"dev010-seed-{args.seed}"
    final_manifest = output / "training_manifest.json"
    if final_manifest.is_file() and (output / "final-adapter").is_dir():
        print(final_manifest.read_text(encoding="utf-8"), end="")
        print("DEV-010 training already complete; existing final adapter retained.")
        return 0
    command = [
        sys.executable, str(BASE / "train_lora.py"),
        "--config", str(CONFIG),
        "--condition", config["primary_condition"],
        "--seed", str(args.seed),
        "--train-file", str(ROOT / "prepared" / "train.jsonl"),
        "--validation-file", str(ROOT / "prepared" / "validation-192.jsonl"),
        "--output", str(output),
    ]
    checkpoint = None if args.restart else latest_checkpoint(output)
    if checkpoint is not None:
        command.extend(["--resume", str(checkpoint)])
        print(f"Resuming seed {args.seed} from {checkpoint}", flush=True)
    subprocess.run(command, cwd=BASE, check=True)
    manifest = json.loads(final_manifest.read_text(encoding="utf-8"))
    manifest.update({
        "schema_version": "cerebrum-dev010-training-manifest.v1",
        "protocol_id": config["protocol_id"],
        "condition": config["primary_condition"],
        "source_dataset": "ACTIONNET-DATA-QUAL-010",
        "parent_failure": "CEREBRUM-DEV-009-RB1",
        "resource_contingent": True,
        "public_scored": False,
        "binding_authority": False,
        "claim_boundary": "Project-authored synthetic queue-integrity and appeal repair training only; no transfer, external, real-institution, production, authority, or IGI claim.",
    })
    write_json(final_manifest, manifest)
    print(json.dumps(manifest, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
