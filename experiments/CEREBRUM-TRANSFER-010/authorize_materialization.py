#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from transfer010 import ROOT, forbidden_materialized_paths, read_json, sha256_path, valid_sha256, write_json


COMMITMENT_FIELDS = [
    "authorship_attestation_commitment",
    "generator_seed_commitment",
    "generator_source_commitment",
    "oracle_source_commitment",
    "governance_form_commitment",
    "renderer_source_commitment",
    "input_commitment",
    "label_commitment",
    "overlap_audit_commitment",
    "power_analysis_commitment",
    "candidate_registry_commitment",
    "baseline_registry_commitment",
    "baseline_contract_commitment",
    "baseline_prompt_pack_commitment",
]
ATTESTATIONS = [
    "instrument_authors_independent_of_actionnet009_010_and_dev009_010",
    "generator_implementer_independent_of_candidate_development",
    "custodian_distinct_from_candidate_and_instrument_authors",
    "no_actionnet001_through_010_code_import",
    "protected_content_unseen_by_candidate_developers",
    "labels_retained_by_custodian",
    "power_analysis_frozen_before_materialization",
]


def main() -> int:
    parser = argparse.ArgumentParser(description="Authorize protected materialization after every frozen prerequisite.")
    parser.add_argument("--custody-commitments", type=Path, required=True)
    args = parser.parse_args()
    candidates = read_json(ROOT / "candidate_registry.json")
    baselines = read_json(ROOT / "baseline_registry.json")
    if candidates.get("status") != "CANDIDATES_FROZEN_DEV010_PASS_VERIFIED":
        raise SystemExit("candidate registry is not frozen after a verified DEV-010 pass")
    if not all(row.get("frozen") and valid_sha256(row.get("adapter_sha256")) for row in candidates["candidates"]):
        raise SystemExit("candidate adapter hashes are incomplete")
    if baselines.get("status") != "LEARNED_BASELINES_FROZEN":
        raise SystemExit("learned baseline registry is not frozen")
    if not all(row.get("frozen") is True and row.get("revision") for row in baselines["conditions"]):
        raise SystemExit("one or more learned baseline identities is incomplete")
    if not valid_sha256(baselines.get("contract_sha256")) or not valid_sha256(baselines.get("prompt_pack_sha256")):
        raise SystemExit("baseline contract or prompt-pack hash is incomplete")
    commitments = read_json(args.custody_commitments)
    if commitments.get("protocol_id") != "CEREBRUM-TRANSFER-010":
        raise SystemExit("custody commitments use the wrong protocol identity")
    missing_hashes = [field for field in COMMITMENT_FIELDS if not valid_sha256(commitments.get(field))]
    if missing_hashes:
        raise SystemExit(f"missing or invalid custody commitments: {missing_hashes}")
    failed_attestations = [field for field in ATTESTATIONS if commitments.get(field) is not True]
    if failed_attestations:
        raise SystemExit(f"independence attestations failed: {failed_attestations}")
    expected = {
        "candidate_registry_commitment": sha256_path(ROOT / "candidate_registry.json"),
        "baseline_registry_commitment": sha256_path(ROOT / "baseline_registry.json"),
        "baseline_contract_commitment": sha256_path(ROOT / "config" / "baseline-contract.json"),
        "baseline_prompt_pack_commitment": baselines["prompt_pack_sha256"],
    }
    mismatched = [key for key, value in expected.items() if commitments.get(key) != value]
    if mismatched:
        raise SystemExit(f"custody commitments mismatch frozen records: {mismatched}")
    premature = forbidden_materialized_paths()
    if premature:
        raise SystemExit(f"premature protected transfer material exists: {premature}")
    authorization = {
        "schema_version": "cerebrum-transfer-010-materialization-authorization.v1",
        "protocol_id": "CEREBRUM-TRANSFER-010",
        "status": "INDEPENDENT_PROTECTED_INSTRUMENT_MATERIALIZATION_AUTHORIZED",
        "candidate_registry_sha256": expected["candidate_registry_commitment"],
        "baseline_registry_sha256": expected["baseline_registry_commitment"],
        "baseline_contract_sha256": expected["baseline_contract_commitment"],
        "baseline_prompt_pack_sha256": expected["baseline_prompt_pack_commitment"],
        "custody_commitments_sha256": sha256_path(args.custody_commitments),
        "commitments": {field: commitments[field] for field in COMMITMENT_FIELDS},
        "attestations": {field: commitments[field] for field in ATTESTATIONS},
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