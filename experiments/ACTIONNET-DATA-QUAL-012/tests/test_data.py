from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_campaign_qualifies() -> None:
    subprocess.run([sys.executable, "run_campaign.py"], cwd=ROOT, check=True)
    report = json.loads((ROOT / "results" / "qualification_report.json").read_text(encoding="utf-8"))
    assert report["status"] == "READY_FOR_CEREBRUM_DEV012_BALANCE_CONTINUATION"
    assert report["controls_passed"] == report["control_count"]
    assert report["audits"]["train"]["records"] == 384
    assert report["audits"]["focused_validation"]["records"] == 64
    assert report["controls"]["training_weights_symmetric"] is True