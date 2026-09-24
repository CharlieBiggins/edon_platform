#!/usr/bin/env python3
"""Fail fast when the GPU image differs from the registered runtime."""

from __future__ import annotations

import importlib.metadata
import json

from dev015_common import CONFIG, read_json


def main() -> int:
    required = read_json(CONFIG)["required_packages"]
    mismatch = {}
    for name, expected in required.items():
        try:
            actual = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            actual = None
        if actual != expected:
            mismatch[name] = {"actual": actual, "required": expected}
    if mismatch:
        raise SystemExit("registered package mismatch: " + json.dumps(mismatch, sort_keys=True))
    print(json.dumps({"status": "REGISTERED_RUNTIME_READY", "packages": required}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())