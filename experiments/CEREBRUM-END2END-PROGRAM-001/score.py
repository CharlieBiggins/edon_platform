#!/usr/bin/env python3
"""Score a frozen Program-001 prediction file."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from program_common import CONFIG, read_json, read_jsonl, sha256_path, write_json
from scoring import evaluate, summarize


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--predictions", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--candidate-id", required=True)
    parser.add_argument("--candidate-step", type=int, required=True)
    parser.add_argument("--gate", choices=("development", "confirmation"), required=True)
    args = parser.parse_args()
    config = read_json(CONFIG)
    expected = read_jsonl(args.input)
    predictions = read_jsonl(args.predictions)
    evaluations = evaluate(expected, predictions)
    result = summarize(evaluations, config[f"{args.gate}_gate"])
    result.update({
        "schema_version": "cerebrum-program-001-score.v1",
        "protocol_id": config["protocol_id"],
        "split": args.gate,
        "candidate_id": args.candidate_id,
        "candidate_step": args.candidate_step,
        "input_sha256": sha256_path(args.input),
        "predictions_sha256": sha256_path(args.predictions),
        "evaluations": evaluations,
        "transfer_authorized": False,
        "binding_authority": False,
    })
    write_json(args.output, result)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())