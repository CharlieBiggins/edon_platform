#!/usr/bin/env python3
"""Validate the Git-facing EDON repository."""

from __future__ import annotations

import json
from pathlib import Path

from edon.cli import validate_repository


if __name__ == "__main__":
    report = validate_repository(Path(".").resolve())
    print(json.dumps(report, indent=2, sort_keys=True))
    raise SystemExit(0 if report["status"] == "PASS" else 1)