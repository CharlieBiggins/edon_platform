from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_campaign_qualifies() -> None:
    subprocess.run([sys.executable, "run_campaign.py"], cwd=ROOT, check=True)
    report = json.loads((ROOT / "results" / "qualification_report.json").read_text(encoding="utf-8"))
    assert report["status"] == "READY_FOR_CEREBRUM_DEV015_MIXED_RETENTION_REPAIR"
    assert report["controls_passed"] == report["control_count"]
    assert report["audits"]["train"]["records"] == 384
    assert report["audits"]["development_selection"]["records"] == 64
    assert report["audits"]["untouched_confirmation"]["records"] == 192
    assert report["controls"]["dev014_cases_disjoint"] is True
    assert report["controls"]["state_reconstruction_tasks_emphasized"] is True