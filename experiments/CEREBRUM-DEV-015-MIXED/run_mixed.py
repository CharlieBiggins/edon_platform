#!/usr/bin/env python3
"""Run training, checkpoint selection, and sealed full confirmation."""

from __future__ import annotations

import subprocess
import sys

from dev015_common import ROOT


def main() -> int:
    for script in (
        "runtime_check.py",
        "train.py",
        "predict_development.py",
        "select_candidate.py",
        "predict_confirmation.py",
        "score.py",
    ):
        subprocess.run([sys.executable, "-u", script], cwd=ROOT, check=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())