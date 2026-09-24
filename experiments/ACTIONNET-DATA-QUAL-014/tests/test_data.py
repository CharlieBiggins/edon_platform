from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_campaign_qualifies() -> None:
    subprocess.run([sys.executable, "run_campaign.py"], cwd=ROOT, check=True)
    report = json.loads((ROOT / "results" / "qualification_report.json").read_text(encoding="utf-8"))
    assert report["status"] == "READY_FOR_CEREBRUM_DEV014_FULL_REGRESSION"
    assert report["controls_passed"] == report["control_count"]
    assert report["audits"]["full_regression"]["records"] == 192
    assert report["audits"]["full_regression"]["task_counts"] == {
        "CERTIFICATE": 48,
        "PAIR_CONTRAST": 48,
        "QUEUE_TRACE": 48,
        "TRANSITION": 48,
    }