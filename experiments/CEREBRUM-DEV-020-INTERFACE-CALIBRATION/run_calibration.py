#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import sys

from dev020_common import ROOT, read_json


def main() -> int:
    for script in ("runtime_check.py", "predict_calibration.py", "score_calibration.py"):
        subprocess.run([sys.executable, "-u", script], cwd=ROOT, check=True)
    selection = read_json(ROOT / "results" / "representation-selection-freeze.json")
    if selection.get("representation_qualified") is not True:
        print(json.dumps({
            "status": "INTERFACE_CALIBRATION_HOLD",
            "heldout_validation_accessed": False,
            "reason": "No candidate representation satisfied every preregistered calibration gate.",
        }, indent=2, sort_keys=True))
        return 0
    for script in ("predict_validation.py", "score_validation.py", "finalize_result.py"):
        subprocess.run([sys.executable, "-u", script], cwd=ROOT, check=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
