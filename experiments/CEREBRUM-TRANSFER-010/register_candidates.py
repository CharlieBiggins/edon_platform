#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from transfer010 import (
    BASE_REVISION,
    DEV_PROTOCOL,
    EXPECTED_SEEDS,
    ROOT,
    read_json,
    sha256_path,
    valid_sha256,
    verify_dev010_summary,
    write_json,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Freeze DEV-010 candidates only after the complete two-seed pass.")
    parser.add_argument("--dev010-summary", type=Path, required=True)
    parser.add_argument("--seed1-training-manifest", type=Path, required=True)
    parser.add_argument("--seed1-prediction-freeze", type=Path, required=True)
    parser.add_argument("--seed1-adapter-sha256", required=True)
    parser.add_argument("--seed2-training-manifest", type=Path, required=True)
    parser.add_argument("--seed2-prediction-freeze", type=Path, required=True)
    parser.add_argument("--seed2-adapter-sha256", required=True)
    args = parser.parse_args()
    summary = read_json(args.dev010_summary)
    verify_dev010_summary(summary)
    rows = []
    for seed, training_path, freeze_path, adapter_hash in (
        (EXPECTED_SEEDS[0], args.seed1_training_manifest, args.seed1_prediction_freeze, args.seed1_adapter_sha256),
        (EXPECTED_SEEDS[1], args.seed2_training_manifest, args.seed2_prediction_freeze, args.seed2_adapter_sha256),
    ):
        if not valid_sha256(adapter_hash):
            raise SystemExit(f"invalid adapter hash for seed {seed}")
        training = read_json(training_path)
        freeze = read_json(freeze_path)
        if training.get("protocol_id") != DEV_PROTOCOL or training.get("seed") != seed:
            raise SystemExit(f"training manifest mismatch for seed {seed}")
        if training.get("base_model_revision") != BASE_REVISION:
            raise SystemExit(f"base revision mismatch for seed {seed}")
        if freeze.get("protocol_id") != DEV_PROTOCOL or freeze.get("seed") != seed:
            raise SystemExit(f"prediction freeze mismatch for seed {seed}")
        if freeze.get("complete") is not True or freeze.get("count") != 192:
            raise SystemExit(f"prediction freeze incomplete for seed {seed}")
        rows.append({
            "condition": f"dev010_seed_{seed}",
            "seed": seed,
            "adapter_sha256": adapter_hash,
            "training_manifest_sha256": sha256_path(training_path),
            "prediction_freeze_sha256": sha256_path(freeze_path),
            "schema_constraint": "SHARED_MODEL_AGNOSTIC_JSON_CONTRACT",
            "retry_budget_per_case": 0,
            "frozen": True,
        })
    registry = {
        "schema_version": "cerebrum-transfer-010-candidate-registry.v1",
        "protocol_id": "CEREBRUM-TRANSFER-010",
        "status": "CANDIDATES_FROZEN_DEV010_PASS_VERIFIED",
        "dev010_summary": {
            "path": str(args.dev010_summary),
            "sha256": sha256_path(args.dev010_summary),
            "status": summary["status"],
            "verified": True,
        },
        "candidates": rows,
        "base_condition": {
            "condition": "unmodified_base",
            "model": "Qwen/Qwen3-4B-Instruct-2507",
            "revision": BASE_REVISION,
            "frozen": True,
        },
        "binding_authority": False,
    }
    write_json(ROOT / "candidate_registry.json", registry)
    print(json.dumps(registry, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())