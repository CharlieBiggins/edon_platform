from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_campaign_qualifies() -> None:
    subprocess.run([sys.executable, "run_campaign.py"], cwd=ROOT, check=True)
    report = json.loads((ROOT / "results" / "qualification_report.json").read_text(encoding="utf-8"))
    assert report["status"] == "READY_FOR_CEREBRUM_DEV013_BOUNDARY_SELECTION"
    assert report["controls_passed"] == report["control_count"]
    assert report["audits"]["train"]["records"] == 192
    assert report["audits"]["development_selection"]["records"] == 32
    assert report["audits"]["untouched_confirmation"]["records"] == 64
    assert report["controls"]["all_pairs_clock_minus_one_vs_plus_one"] is True
    assert report["controls"]["safety_weight_exceeds_allow_weight"] is True
