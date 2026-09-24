#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from transfer008 import EXPECTED_SEEDS, ROOT, read_json, sha256_path, valid_sha256, verify_rb1_summary, write_json


def main() -> int:
    parser = argparse.ArgumentParser(description="Freeze RB1 candidates only after the registered two-seed pass.")
    parser.add_argument("--rb1-summary", type=Path, required=True)
    parser.add_argument("--seed1-training-manifest", type=Path, required=True)
    parser.add_argument("--seed1-prediction-freeze", type=Path, required=True)
    parser.add_argument("--seed1-adapter-sha256", required=True)
    parser.add_argument("--seed2-training-manifest", type=Path, required=True)
    parser.add_argument("--seed2-prediction-freeze", type=Path, required=True)
    parser.add_argument("--seed2-adapter-sha256", required=True)
    parser.add_argument("--base-revision", required=True)
    parser.add_argument("--baseline-prompt-pack-sha256", required=True)
    args = parser.parse_args()
    if not valid_sha256(args.baseline_prompt_pack_sha256):
        raise SystemExit("invalid baseline prompt-pack hash")
    summary = read_json(args.rb1_summary)
    verify_rb1_summary(summary)
    rows = []
    for seed, training_path, freeze_path, adapter_hash in (
        (EXPECTED_SEEDS[0], args.seed1_training_manifest, args.seed1_prediction_freeze, args.seed1_adapter_sha256),
        (EXPECTED_SEEDS[1], args.seed2_training_manifest, args.seed2_prediction_freeze, args.seed2_adapter_sha256),
    ):
        if not valid_sha256(adapter_hash):
            raise SystemExit(f"invalid adapter hash for seed {seed}")
        training = read_json(training_path)
        freeze = read_json(freeze_path)
        if training.get("protocol_id") != "CEREBRUM-DEV-009-RB1" or training.get("seed") != seed:
            raise SystemExit(f"training manifest mismatch for seed {seed}")
        if freeze.get("protocol_id") != "CEREBRUM-DEV-009-RB1" or freeze.get("seed") != seed:
            raise SystemExit(f"prediction freeze mismatch for seed {seed}")
        if freeze.get("complete") is not True or freeze.get("count") != 192:
            raise SystemExit(f"prediction freeze incomplete for seed {seed}")
        rows.append({
            "condition": f"rb1_seed_{seed}",
            "seed": seed,
            "adapter_sha256": adapter_hash,
            "training_manifest_sha256": sha256_path(training_path),
            "prediction_freeze_sha256": sha256_path(freeze_path),
            "schema_constraint": "SHARED_MODEL_AGNOSTIC_JSON_SCHEMA",
            "retry_budget_per_case": 0,
            "frozen": True,
        })
    registry = {
        "schema_version": "cerebrum-transfer-008-candidate-registry.v1",
        "protocol_id": "CEREBRUM-TRANSFER-008",
        "status": "CANDIDATES_FROZEN_RB1_PASS_VERIFIED",
        "rb1_summary": {
            "path": str(args.rb1_summary),
            "sha256": sha256_path(args.rb1_summary),
            "status": summary["status"],
            "verified": True,
        },
        "candidates": rows,
        "base_condition": {
            "condition": "unmodified_base",
            "model": "Qwen/Qwen3-4B-Instruct-2507",
            "revision": args.base_revision,
            "frozen": True,
        },
        "binding_authority": False,
    }
    write_json(ROOT / "candidate_registry.json", registry)
    contract_path = ROOT / "config" / "baseline-contract.json"
    contract_hash = sha256_path(contract_path)
    baselines = {
        "schema_version": "cerebrum-transfer-008-baseline-registry.v1",
        "protocol_id": "CEREBRUM-TRANSFER-008",
        "amendment_id": "CEREBRUM-TRANSFER-008-AMENDMENT-001-BASELINE-FAIRNESS",
        "status": "LEARNED_BASELINES_FROZEN",
        "contract_path": "config/baseline-contract.json",
        "contract_sha256": contract_hash,
        "prompt_pack_sha256": args.baseline_prompt_pack_sha256,
        "conditions": [
            {
                "condition": "unmodified_base",
                "model": "Qwen/Qwen3-4B-Instruct-2507",
                "revision": args.base_revision,
                "adapter_sha256": None,
                "schema_constraint": False,
                "interface_demonstrations": False,
                "primary_superiority_eligible": False,
                "frozen": True,
            },
            {
                "condition": "interface_matched_base",
                "model": "Qwen/Qwen3-4B-Instruct-2507",
                "revision": args.base_revision,
                "adapter_sha256": None,
                "schema_constraint": True,
                "interface_demonstrations": False,
                "primary_superiority_eligible": True,
                "frozen": True,
            },
            {
                "condition": "prompted_interface_matched_base",
                "model": "Qwen/Qwen3-4B-Instruct-2507",
                "revision": args.base_revision,
                "adapter_sha256": None,
                "schema_constraint": True,
                "interface_demonstrations": True,
                "primary_superiority_eligible": True,
                "frozen": True,
            },
        ],
        "binding_authority": False,
    }
    write_json(ROOT / "baseline_registry.json", baselines)
    print(json.dumps({"candidate_registry": registry, "baseline_registry": baselines}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())