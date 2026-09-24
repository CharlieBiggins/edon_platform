#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from cerebrum_eventnet_data import ACTIONNET, ROOT, prepare


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--actionnet-root", type=Path, default=ACTIONNET)
    parser.add_argument("--output", type=Path, default=ROOT / "prepared")
    args = parser.parse_args()
    manifest = prepare(args.actionnet_root, args.output)
    print(json.dumps(manifest, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())