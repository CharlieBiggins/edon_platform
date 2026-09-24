#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from transfer008 import ROOT, forbidden_materialized_paths, read_json, sha256_path, valid_sha256, write_json


COMMITMENT_FIELDS = [
    "generator_seed_commitment",
    "generator_source_commitment",
    "oracle_source_commitment",
    "input_commitment",
    "label_commitment",
    "overlap_audit_commitment",
    "candidate_registry_commitment",
    "baseline_registry_commitment",
    "baseline_contract_commitment",
    "baseline_prompt_pack_commitment",
]


def main() -> int:
    parser = argparse.ArgumentParser(description="Authorize independent materialization after candidate and custody gates.")
    parser.add_argument("--custody-commitments", type=Path, required=True)
    args = parser.parse_args()
    registry = read_json(ROOT / "candidate_registry.json")
    baseline_registry = read_json(ROOT / "baseline_registry.json")
    if registry.get("status") != "CANDIDATES_FROZEN_RB1_PASS_VERIFIED":
        raise SystemExit("candidate registry is not frozen after a verified RB1 pass")
    if not all(row.get("frozen") and valid_sha256(row.get("adapter_sha256")) for row in registry["candidates"]):
        raise SystemExit("candidate adapter hashes are incomplete")
    if baseline_registry.get("status") != "LEARNED_BASELINES_FROZEN":
        raise SystemExit("learned baseline registry is not frozen")
    if not all(row.get("frozen") is True and row.get("revision") for row in baseline_registry["conditions"]):
        raise SystemExit("one or more learned baseline conditions are not frozen")
    if not valid_sha256(baseline_registry.get("contract_sha256")) or not valid_sha256(baseline_registry.get("prompt_pack_sha256")):
        raise SystemExit("baseline contract or prompt-pack hash is incomplete")
    commitments = read_json(args.custody_commitments)
    missing = [field for field in COMMITMENT_FIELDS if not valid_sha256(commitments.get(field))]
    if missing:
        raise SystemExit(f"missing or invalid custody commitments: {missing}")
    expected_commitments = {
        "candidate_registry_commitment": sha256_path(ROOT / "candidate_registry.json"),
        "baseline_registry_commitment": sha256_path(ROOT / "baseline_registry.json"),
        "baseline_contract_commitment": sha256_path(ROOT / "config" / "baseline-contract.json"),
        "baseline_prompt_pack_commitment": baseline_registry["prompt_pack_sha256"],
    }
    mismatched = [key for key, value in expected_commitments.items() if commitments.get(key) != value]
    if mismatched:
        raise SystemExit(f"custody commitments do not match frozen baseline/candidate records: {mismatched}")
    premature = forbidden_materialized_paths()
    if premature:
        raise SystemExit(f"premature transfer material exists: {premature}")
    authorization = {
        "schema_version": "cerebrum-transfer-008-materialization-authorization.v1",
        "protocol_id": "CEREBRUM-TRANSFER-008",
        "status": "INDEPENDENT_INSTRUMENT_MATERIALIZATION_AUTHORIZED",
        "candidate_registry_sha256": expected_commitments["candidate_registry_commitment"],
        "baseline_registry_sha256": expected_commitments["baseline_registry_commitment"],
        "baseline_contract_sha256": expected_commitments["baseline_contract_commitment"],
        "baseline_prompt_pack_sha256": expected_commitments["baseline_prompt_pack_commitment"],
        "commitments": {field: commitments[field] for field in COMMITMENT_FIELDS},
        "cases_authorized": 192,
        "labels_remain_in_independent_custody": True,
        "score_authorized": False,
        "binding_authority": False,
    }
    write_json(ROOT / "materialization_authorization.json", authorization)
    print(json.dumps(authorization, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())