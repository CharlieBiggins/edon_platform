from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_campaign_qualifies() -> None:
    subprocess.run([sys.executable, "run_campaign.py"], cwd=ROOT, check=True)
    report = json.loads((ROOT / "results" / "qualification_report.json").read_text(encoding="utf-8"))
    assert report["status"] == "READY_FOR_CEREBRUM_DEV011_FOCUSED_CONTINUATION"
    assert report["controls_passed"] == report["control_count"]
    assert report["audits"]["train"]["records"] == 768
    assert report["audits"]["focused_validation"]["records"] == 64