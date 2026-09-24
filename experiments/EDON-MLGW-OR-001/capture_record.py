#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from mlgw_program import ROOT, append_record


def main() -> int:
    parser = argparse.ArgumentParser(description="Append one hash-chained public or custodied timeline record.")
    parser.add_argument("--ledger", type=Path, default=ROOT / "data" / "public_event_ledger.jsonl")
    parser.add_argument("--record-id", required=True)
    parser.add_argument("--event-id", default="MEMPHIS-BOW-ECHO-2026-08-22")
    parser.add_argument("--record-type", required=True)
    parser.add_argument("--evidence-class", choices=["OBSERVED", "DERIVED", "ESTIMATED", "TARGET", "PILOT_MEASURED"], required=True)
    parser.add_argument("--event-time", required=True)
    parser.add_argument("--available-at", required=True)
    parser.add_argument("--source-id")
    parser.add_argument("--payload-json", required=True)
    parser.add_argument("--derivation-json")
    parser.add_argument("--confidence", type=float)
    parser.add_argument("--authoritative", action="store_true")
    parser.add_argument("--supersedes")
    args = parser.parse_args()
    record = {
        "record_id": args.record_id,
        "event_id": args.event_id,
        "record_type": args.record_type,
        "evidence_class": args.evidence_class,
        "event_time": args.event_time,
        "available_at": args.available_at,
        "source_id": args.source_id,
        "payload": json.loads(args.payload_json),
        "derivation": json.loads(args.derivation_json) if args.derivation_json else None,
        "confidence": args.confidence,
        "authoritative": args.authoritative,
        "training_eligible": False,
        "supersedes": args.supersedes,
    }
    sealed = append_record(args.ledger, record)
    print(json.dumps(sealed, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())