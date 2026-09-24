#!/usr/bin/env python3
"""Apply the preregistered CEREBRUM-DEV-009 two-seed advancement rule."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


REGISTERED_SEEDS = {26082491, 26082492}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--evaluation", type=Path, action="append", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    reports = [json.loads(path.read_text(encoding="utf-8")) for path in args.evaluation]
    seeds = {report.get("seed") for report in reports}
    condition = {report.get("condition") for report in reports}
    checks = {
        "exactly_two_reports": len(reports) == 2,
        "registered_seeds_present": seeds == REGISTERED_SEEDS,
        "single_condition": len(condition) == 1,
        "primary_condition": condition == {"multi_generator_execution_repair"},
        "both_seed_gates_pass": len(reports) == 2 and all(report.get("advancement_gate", {}).get("passed") is True for report in reports),
        "no_public_score": all(report.get("public_scored") is False for report in reports),
    }
    passed = all(checks.values())
    result = {
        "schema_version": "cerebrum-execution-transfer-repair-two-seed-summary.v1",
        "protocol_id": "CEREBRUM-DEV-009",
        "condition": next(iter(condition)) if len(condition) == 1 else None,
        "seeds": sorted(seed for seed in seeds if isinstance(seed, int)),
        "checks": checks,
        "checks_passed": sum(checks.values()),
        "check_count": len(checks),
        "status": "READY_FOR_NEW_INDEPENDENT_TRANSFER_SUCCESSOR" if passed else "HOLD_FOR_ADDITIVE_REPAIR",
        "independent_evaluation_authorized": passed,
        "public_scoring_authorized": False,
        "binding_authority": False,
        "claim_boundary": "Two-seed fresh-lineage internal synthetic execution-transfer repair disposition only; independent, public, protected, and real-institution evaluation remain separate.",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())