#!/usr/bin/env python3
"""Run the resumable 24-step continuation, prediction, and focused score."""

from __future__ import annotations

import subprocess
import sys

from dev012_common import ROOT


def main() -> int:
    subprocess.run([sys.executable, "train.py"], cwd=ROOT, check=True)
    subprocess.run([sys.executable, "predict.py"], cwd=ROOT, check=True)
    subprocess.run([sys.executable, "score.py"], cwd=ROOT, check=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())