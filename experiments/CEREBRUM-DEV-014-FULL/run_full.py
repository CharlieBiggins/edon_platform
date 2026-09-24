#!/usr/bin/env python3
"""Run the registered runtime check, full prediction, and scoring."""

from __future__ import annotations

import subprocess
import sys

from dev014_common import ROOT


def main() -> int:
    for script in ("runtime_check.py", "predict.py", "score.py"):
        subprocess.run([sys.executable, "-u", script], cwd=ROOT, check=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())