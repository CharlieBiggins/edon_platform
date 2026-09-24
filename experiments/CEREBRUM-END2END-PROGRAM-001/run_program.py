#!/usr/bin/env python3
"""Run the registered Program-001 training, selection, and confirmation flow."""

from __future__ import annotations

import subprocess
import sys

from program_common import ROOT


def main() -> int:
    for script in (
        "runtime_check.py",
        "preflight.py",
        "predict_base_development.py",
        "train.py",
        "predict_development.py",
        "select_candidate.py",
        "predict_confirmation.py",
        "finalize.py",
    ):
        subprocess.run([sys.executable, "-u", script], cwd=ROOT, check=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())