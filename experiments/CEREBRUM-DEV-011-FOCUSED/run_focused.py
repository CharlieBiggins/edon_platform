#!/usr/bin/env python3
"""Run both resumable continuation/prediction jobs and then score them."""

from __future__ import annotations

import subprocess
import sys

from dev011_common import CONFIG, ROOT, read_json


def main() -> int:
    config = read_json(CONFIG)
    for spec in config["registered_runs"]:
        seed = str(spec["continuation_seed"])
        subprocess.run([sys.executable, "train.py", "--seed", seed], cwd=ROOT, check=True)
        subprocess.run([sys.executable, "predict.py", "--seed", seed], cwd=ROOT, check=True)
    subprocess.run([sys.executable, "score.py"], cwd=ROOT, check=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())