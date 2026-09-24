#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

from mlgw_program import ROOT, read_jsonl, sha256_path, validate_ledger, write_json


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ledger", type=Path, default=ROOT / "data" / "public_event_ledger.jsonl")
    parser.add_argument("--output", type=Path, default=ROOT / "results" / "public_timeline_freeze.json")
    parser.add_argument("--role", default="PUBLIC_DEVELOPMENT_REPLAY")
    args = parser.parse_args()
    rows = read_jsonl(args.ledger)
    chain = validate_ledger(rows)
    manifest = {
        "schema_version": "edon-mlgw-timeline-freeze.v1",
        "protocol_id": "EDON-MLGW-OR-001",
        "event_id": "MEMPHIS-BOW-ECHO-2026-08-22",
        "role": args.role,
        "ledger_sha256": sha256_path(args.ledger),
        "chain": chain,
        "evidence_class_counts": dict(sorted(Counter(row["evidence_class"] for row in rows).items())),
        "authoritative_records": sum(row["authoritative"] is True for row in rows),
        "training_eligible_records": sum(row["training_eligible"] is True for row in rows),
        "protected": False,
        "prospective": False,
        "binding_authority": False,
        "claim_boundary": "Public-source development timeline only; not the authoritative internal MLGW information or decision state."
    }
    write_json(args.output, manifest)
    print(json.dumps(manifest, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())