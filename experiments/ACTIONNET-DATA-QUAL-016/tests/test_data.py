from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_campaign_qualifies() -> None:
    subprocess.run([sys.executable, "run_campaign.py"], cwd=ROOT, check=True)
    report = json.loads((ROOT / "results" / "qualification_report.json").read_text(encoding="utf-8"))
    assert report["status"] == "READY_FOR_CEREBRUM_DEV016_NARROW_REPAIR"
    assert report["controls_passed"] == report["control_count"] == 33
    assert report["audits"]["train"]["records"] == 368
    assert report["audits"]["development_selection"]["records"] == 64
    assert report["audits"]["untouched_confirmation"]["records"] == 192
    assert report["controls"]["delayed_evidence_certificate_balance"] is True
    assert report["controls"]["previous_validation_namespace_disjoint"] is True
    assert report["controls"]["previous_validation_families_and_renderers_disjoint"] is True
    assert report["controls"]["transition_and_queue_trace_count_96"] is True