#!/usr/bin/env python3
"""Run frozen-model prediction, target-blind verification, and sealed scoring."""

from __future__ import annotations

import subprocess
import sys

from dev018_common import ROOT


def main() -> int:
    commands = (
        [sys.executable, "-u", "runtime_check.py"],
        [sys.executable, "-u", "predict_development.py"],
        [sys.executable, "-u", "verify_split.py", "--split", "development"],
        [sys.executable, "-u", "score_development.py"],
        [sys.executable, "-u", "predict_confirmation.py"],
        [sys.executable, "-u", "verify_split.py", "--split", "confirmation"],
        [sys.executable, "-u", "score_confirmation.py"],
    )
    for command in commands:
        subprocess.run(command, cwd=ROOT, check=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())