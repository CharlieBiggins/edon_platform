#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from transfer010 import BASE_REVISION, ROOT, read_json, sha256_path, valid_sha256, write_json


FRONTIER_CONDITIONS = ["frontier_general_primary", "frontier_general_secondary"]


def main() -> int:
    parser = argparse.ArgumentParser(description="Freeze matched Qwen and two-provider frontier baselines.")
    parser.add_argument("--frontier-commitments", type=Path, required=True)
    parser.add_argument("--baseline-prompt-pack-sha256", required=True)
    args = parser.parse_args()
    candidates = read_json(ROOT / "candidate_registry.json")
    if candidates.get("status") != "CANDIDATES_FROZEN_DEV010_PASS_VERIFIED":
        raise SystemExit("DEV-010 candidates are not frozen after a verified pass")
    if not valid_sha256(args.baseline_prompt_pack_sha256):
        raise SystemExit("invalid baseline prompt-pack hash")
    frontier = read_json(args.frontier_commitments)
    rows = frontier.get("conditions")
    if not isinstance(rows, list) or [row.get("condition") for row in rows] != FRONTIER_CONDITIONS:
        raise SystemExit("frontier commitments must contain the two registered conditions in order")
    if len({row.get("provider") for row in rows}) != 2 or None in {row.get("provider") for row in rows}:
        raise SystemExit("frontier baselines must use two distinct named providers")
    for row in rows:
        if not all(isinstance(row.get(key), str) and row[key] for key in ("provider", "model", "revision")):
            raise SystemExit(f"incomplete frontier model identity for {row.get('condition')}")
        if not valid_sha256(row.get("interface_contract_sha256")) or not valid_sha256(row.get("selection_rule_sha256")):
            raise SystemExit(f"invalid frontier commitments for {row['condition']}")
    contract_path = ROOT / "config" / "baseline-contract.json"
    registry = {
        "schema_version": "cerebrum-transfer-010-baseline-registry.v1",
        "protocol_id": "CEREBRUM-TRANSFER-010",
        "status": "LEARNED_BASELINES_FROZEN",
        "contract_path": "config/baseline-contract.json",
        "contract_sha256": sha256_path(contract_path),
        "prompt_pack_sha256": args.baseline_prompt_pack_sha256,
        "conditions": [
            {
                "condition": "unmodified_base",
                "provider": "local",
                "model": "Qwen/Qwen3-4B-Instruct-2507",
                "revision": BASE_REVISION,
                "schema_constraint": False,
                "interface_demonstrations": False,
                "primary_superiority_eligible": False,
                "frozen": True,
            },
            {
                "condition": "interface_matched_base",
                "provider": "local",
                "model": "Qwen/Qwen3-4B-Instruct-2507",
                "revision": BASE_REVISION,
                "schema_constraint": True,
                "interface_demonstrations": False,
                "primary_superiority_eligible": True,
                "frozen": True,
            },
            {
                "condition": "prompted_interface_matched_base",
                "provider": "local",
                "model": "Qwen/Qwen3-4B-Instruct-2507",
                "revision": BASE_REVISION,
                "schema_constraint": True,
                "interface_demonstrations": True,
                "primary_superiority_eligible": True,
                "frozen": True,
            },
            *[
                {
                    **row,
                    "schema_constraint": True,
                    "interface_demonstrations": False,
                    "primary_superiority_eligible": True,
                    "frozen": True,
                }
                for row in rows
            ],
        ],
        "binding_authority": False,
    }
    write_json(ROOT / "baseline_registry.json", registry)
    print(json.dumps(registry, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())