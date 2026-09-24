#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from mlgw_program import compare_episodes, read_json, write_json


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = compare_episodes(read_json(args.baseline), read_json(args.candidate))
    write_json(args.output, result)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())