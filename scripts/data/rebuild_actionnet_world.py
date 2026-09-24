#!/usr/bin/env python3
"""Rebuild and verify the complete ActionNet-001 through ActionNet-008 world."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path


REPO = Path(__file__).resolve().parents[2]
VERSIONS = ("001", "002", "003", "004", "005", "006", "007", "008")


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify_package(version: str) -> dict[str, object]:
    package = REPO / "experiments" / f"ACTIONNET-DATA-QUAL-{version}"
    report = json.loads((package / "results" / "qualification_report.json").read_text())
    if report["controls_passed"] != report["control_count"] or not all(report["controls"].values()):
        raise RuntimeError(f"ActionNet {version} qualification controls failed")
    checked = 0
    checksum_file = package / "results" / "checksums.sha256"
    result_manifest = json.loads((package / "results" / "result_manifest.json").read_text())
    if checksum_file.is_file():
        inventory = [line.split("  ", 1) for line in checksum_file.read_text().splitlines()]
    else:
        inventory = [
            (value.removeprefix("sha256:"), relative)
            for relative, value in result_manifest["artifacts"].items()
        ]
    for expected, relative in inventory:
        artifact = package / relative
        if not artifact.is_file() or digest(artifact) != expected:
            raise RuntimeError(f"ActionNet {version} checksum mismatch: {relative}")
        checked += 1
    manifest = json.loads((package / "results" / "dataset_manifest.json").read_text())
    return {
        "version": version,
        "result_id": report["result_id"],
        "status": report["status"],
        "controls": f'{report["controls_passed"]}/{report["control_count"]}',
        "counts": manifest.get("counts") or report.get("counts", {}),
        "checksums_verified": checked,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--verify-only",
        action="store_true",
        help="verify the existing materialized world without regenerating it",
    )
    args = parser.parse_args()
    if not args.verify_only:
        subprocess.run([sys.executable, "scripts/data/import_actionnet_world.py"], cwd=REPO, check=True)
        for version in VERSIONS:
            package = REPO / "experiments" / f"ACTIONNET-DATA-QUAL-{version}"
            subprocess.run([sys.executable, "run_campaign.py"], cwd=package, check=True)
    summaries = [verify_package(version) for version in VERSIONS]
    print(json.dumps({
        "status": "COMPLETE_ACTIONNET_WORLD_VERIFIED",
        "binding_authority": False,
        "versions": summaries,
        "custody_boundary": (
            "ActionNet-008 is an authoring and governance world with zero training-eligible "
            "records. Reserved future-public and protected families are intentionally "
            "unmaterialized."
        ),
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())