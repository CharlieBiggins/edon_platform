#!/usr/bin/env python3
from __future__ import annotations

import importlib.metadata
import json

from program_common import CONFIG, read_json


def main() -> int:
    required = read_json(CONFIG)["required_packages"]
    mismatches = {}
    for name, expected in required.items():
        try:
            actual = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            actual = None
        if actual != expected:
            mismatches[name] = {"actual": actual, "required": expected}
    if mismatches:
        raise SystemExit("registered package mismatch: " + json.dumps(mismatches, sort_keys=True))
    print(json.dumps({"status": "REGISTERED_RUNTIME_READY", "packages": required}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())