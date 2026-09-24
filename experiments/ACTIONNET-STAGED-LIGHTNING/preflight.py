"""CPU-only aggregate preflight for the staged Lightning upload."""
from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
EXPERIMENTS = ROOT / "experiments"
COMMANDS = {
    "matched001": EXPERIMENTS / "CEREBRUM-ACTIONNET-MATCHED-001/run.py",
    "matched002": EXPERIMENTS / "CEREBRUM-ACTIONNET-MATCHED-002/run.py",
    "transfer001": EXPERIMENTS / "CEREBRUM-ACTIONNET-TRANSFER-001/run.py",
    "closed_loop_feasibility001": EXPERIMENTS / "CEREBRUM-CLOSED-LOOP-FEASIBILITY-001/run.py",
}


def main():
    reports = {}
    for name, path in COMMANDS.items():
        completed = subprocess.run([sys.executable, "-B", str(path), "preflight"],
            cwd=ROOT.parent, text=True, encoding="utf-8", capture_output=True)
        if completed.returncode != 0:
            raise RuntimeError(name + " preflight failed:\n" + completed.stderr)
        reports[name] = json.loads(completed.stdout)
    report = {"schema_version": 1, "date": "2026-09-19",
        "status": "SOURCE_FRAMEWORKS_VERIFIED_BLOCKED_BEFORE_PAID_EXECUTION",
        "reports": reports, "gpu_started": False, "network_used": False,
        "protected_transfer_material_present": False, "binding_authority": False}
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()