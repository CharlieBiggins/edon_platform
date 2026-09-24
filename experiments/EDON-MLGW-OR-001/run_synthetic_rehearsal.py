#!/usr/bin/env python3
from __future__ import annotations

import json

from mlgw_program import ROOT, compare_episodes, write_json
from simulator import simulate


def synthetic_world() -> dict:
    return {
        "world_id": "SYNTHETIC-MLGW-PLUMBING-ONLY",
        "event_id": "NOT-A-REAL-STORM",
        "start_time": "2026-08-24T00:00:00-05:00",
        "initial_customers_out": 1000,
        "crews": [
            {"crew_id": "crew-a-tree", "capabilities": ["TREE"], "available_minute": 0},
            {"crew_id": "crew-z-line", "capabilities": ["LINE"], "available_minute": 0}
        ],
        "jobs": [
            {
                "job_id": "tree-clearance",
                "customers_restored": 0,
                "duration_minutes": 60,
                "required_capability": "TREE",
                "dependencies": [],
                "available_minute": 0,
                "critical_weight": 0,
                "safety_validated": True,
                "actual_priority": 1
            },
            {
                "job_id": "small-service",
                "customers_restored": 20,
                "duration_minutes": 180,
                "required_capability": "LINE",
                "dependencies": [],
                "available_minute": 60,
                "critical_weight": 0,
                "safety_validated": True,
                "actual_priority": 1
            },
            {
                "job_id": "main-feeder",
                "customers_restored": 700,
                "duration_minutes": 120,
                "required_capability": "LINE",
                "dependencies": ["tree-clearance"],
                "available_minute": 0,
                "critical_weight": 2,
                "safety_validated": True,
                "actual_priority": 3
            },
            {
                "job_id": "critical-pump",
                "customers_restored": 100,
                "duration_minutes": 60,
                "required_capability": "LINE",
                "dependencies": ["tree-clearance"],
                "available_minute": 0,
                "critical_weight": 5,
                "safety_validated": True,
                "actual_priority": 4
            },
            {
                "job_id": "downstream-lateral",
                "customers_restored": 180,
                "duration_minutes": 60,
                "required_capability": "LINE",
                "dependencies": ["main-feeder"],
                "available_minute": 0,
                "critical_weight": 0,
                "safety_validated": True,
                "actual_priority": 5
            }
        ],
        "binding_authority": False
    }


def main() -> int:
    world = synthetic_world()
    actual = simulate(world, "actual_mlgw_replay")
    heuristic = simulate(world, "critical_biggest_return")
    comparison = compare_episodes(actual, heuristic)
    result = {
        "schema_version": "edon-mlgw-synthetic-rehearsal.v1",
        "protocol_id": "EDON-MLGW-OR-001",
        "actual_replay": actual,
        "heuristic": heuristic,
        "comparison": comparison,
        "status": "SYNTHETIC_PLUMBING_REHEARSAL_PASS" if comparison["valid_matched_resources"] and comparison["candidate_safety_gate_passed"] else "FAIL",
        "claim_boundary": "Invented fixture only; no MLGW fact, controller result, transfer evidence, or restoration claim."
    }
    write_json(ROOT / "results" / "synthetic_rehearsal.json", result)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["status"].endswith("PASS") else 1


if __name__ == "__main__":
    raise SystemExit(main())