#!/usr/bin/env python3
"""Verify one complete model prediction split and freeze its audit trail."""

from __future__ import annotations

import argparse
import json

from dev018_common import ROOT, read_jsonl, sha256_path, write_json, write_jsonl
from verifier import verify_predictions


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--split", choices=("development", "confirmation"), required=True)
    args = parser.parse_args()
    if args.split == "development":
        expected_count = 64
        verifier_input = ROOT / "prepared" / "development-verifier-inputs-64.jsonl"
    else:
        expected_count = 192
        verifier_input = ROOT / "prepared" / "confirmation-verifier-inputs-192.jsonl"
    model_path = ROOT / "results" / f"{args.split}-model-predictions.jsonl"
    verified_path = ROOT / "results" / f"{args.split}-verified-predictions.jsonl"
    audit_path = ROOT / "results" / f"{args.split}-verification-audit.jsonl"
    verifier_inputs = read_jsonl(verifier_input)
    model_predictions = read_jsonl(model_path)
    if len(verifier_inputs) != expected_count or len(model_predictions) != expected_count:
        raise SystemExit(f"incomplete {args.split} inputs or model predictions")
    verified, audits = verify_predictions(verifier_inputs, model_predictions)
    write_jsonl(verified_path, verified)
    write_jsonl(audit_path, audits)
    accepted = sum(row["action"] == "ACCEPT_MODEL" for row in audits)
    overrides = expected_count - accepted
    safety_overrides = sum(row["safety_override"] for row in audits)
    freeze = {
        "schema_version": "cerebrum-dev018-verification-freeze.v1",
        "protocol_id": "CEREBRUM-DEV-018-VERIFIED",
        "split": args.split,
        "count": expected_count,
        "complete": len(verified) == len(audits) == expected_count,
        "verifier_input_sha256": sha256_path(verifier_input),
        "model_predictions_sha256": sha256_path(model_path),
        "verified_predictions_sha256": sha256_path(verified_path),
        "verification_audit_sha256": sha256_path(audit_path),
        "accepted_model_outputs": accepted,
        "overridden_model_outputs": overrides,
        "model_acceptance_rate": accepted / expected_count,
        "safety_overrides": safety_overrides,
        "all_answer_key_access_flags_false": all(row["answer_key_accessed"] is False for row in audits),
        "all_outputs_bound_to_executor": all(
            row["action"] in {"ACCEPT_MODEL", "OVERRIDE_WITH_EXECUTOR"} for row in audits
        ),
        "binding_authority": False,
        "transfer_authorized": False,
    }
    write_json(ROOT / "results" / f"{args.split}-verification-freeze.json", freeze)
    print(json.dumps(freeze, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())