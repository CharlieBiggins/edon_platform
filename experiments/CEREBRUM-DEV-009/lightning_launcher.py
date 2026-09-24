#!/usr/bin/env python3
"""Explicit-stage EventNet launcher with no public/protected scoring stage."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent
REGISTERED_CONDITIONS = ("multi_generator_execution_repair",)


def run(*arguments: str) -> None:
    command = [sys.executable, *arguments]
    print("+", " ".join(command), flush=True)
    subprocess.run(command, cwd=ROOT, check=True)


def latest_checkpoint(output: Path) -> Path | None:
    checkpoints = [path for path in output.glob("checkpoint-*") if path.is_dir()]
    if not checkpoints:
        return None
    return max(checkpoints, key=lambda path: int(path.name.rsplit("-", 1)[-1]))


def main() -> int:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="stage", required=True)
    subparsers.add_parser("probe")
    subparsers.add_parser("install")
    subparsers.add_parser("prepare")
    subparsers.add_parser("base")
    subparsers.add_parser("rules")
    for name in ("smoke", "train"):
        stage = subparsers.add_parser(name)
        stage.add_argument("--condition", choices=REGISTERED_CONDITIONS, default="multi_generator_execution_repair")
        stage.add_argument("--seed", type=int)
    args = parser.parse_args()
    if args.stage == "probe":
        run("hardware_probe.py", "--output", "results/lightning-hardware.json")
        run("preflight.py")
    elif args.stage == "install":
        run("-m", "pip", "install", "-r", "requirements-lightning.txt")
    elif args.stage == "prepare":
        run("prepare_data.py")
        run("preflight.py")
    elif args.stage == "base":
        prediction = "results/base-fresh-validation-predictions.jsonl"
        run("predict.py", "--input", "prepared/fresh-validation-all.jsonl", "--output", prediction, "--load-in-4bit")
        run("evaluate.py", "--predictions", prediction, "--condition", "unmodified_base", "--output", "results/base-fresh-validation-evaluation.json")
    elif args.stage == "rules":
        run("preflight.py")
    elif args.stage == "smoke":
        command = ["train_lora.py", "--smoke-test", "--condition", args.condition]
        if args.seed is not None:
            command.extend(["--seed", str(args.seed)])
        run(*command)
    elif args.stage == "train":
        if args.seed is None:
            raise SystemExit("--seed is required for a registered training run")
        training_root = ROOT / "artifacts" / f"{args.condition}-seed-{args.seed}"
        artifact = f"artifacts/{args.condition}-seed-{args.seed}/final-adapter"
        prediction = f"results/{args.condition}-seed-{args.seed}-predictions.jsonl"
        evaluation = f"results/{args.condition}-seed-{args.seed}-evaluation.json"
        if (training_root / "training_manifest.json").exists() and (training_root / "final-adapter").exists():
            print(f"+ completed training artifact found; reusing {artifact}", flush=True)
        else:
            command = ["train_lora.py", "--condition", args.condition, "--seed", str(args.seed)]
            checkpoint = latest_checkpoint(training_root)
            if checkpoint is not None:
                command.extend(["--resume", str(checkpoint)])
                print(f"+ resuming training from {checkpoint}", flush=True)
            run(*command)
        run("predict.py", "--adapter", artifact, "--input", "prepared/fresh-validation-all.jsonl", "--output", prediction, "--load-in-4bit")
        run("evaluate.py", "--predictions", prediction, "--condition", args.condition, "--seed", str(args.seed), "--output", evaluation)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())