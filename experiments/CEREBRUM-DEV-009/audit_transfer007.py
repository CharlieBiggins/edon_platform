#!/usr/bin/env python3
"""Validate the Transfer-007 smoke failure that motivates DEV-009."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent


def audit(observed: dict[str, Any]) -> dict[str, Any]:
    checks = {
        "source_protocol_transfer007": observed.get("source_protocol") == "CEREBRUM-TRANSFER-007-STAGED-DIAGNOSTIC",
        "smoke_gate_failed": observed.get("source_status") == "SMOKE_GATE_FAIL_STOP_AND_REPAIR",
        "candidate_gate_failed": observed.get("checks_passed", 16) < observed.get("check_count", 16),
        "certificate_signal_nontrivial": observed.get("certificate_decision_accuracy", 0.0) >= 0.65,
        "transition_state_below_0_40": observed.get("transition_exact_match", 1.0) < 0.40,
        "queue_exact_below_0_10": observed.get("queue_exact_match", 1.0) < 0.10,
        "pair_exact_zero": observed.get("pair_exact_match") == 0.0,
        "unsafe_authorizations_present": observed.get("unsafe_authorizations", 0) > 0,
        "case_reuse_prohibited": observed.get("case_reuse_authorized") is False,
        "binding_authority_false": observed.get("binding_authority") is False,
    }
    passed = all(checks.values())
    return {
        "schema_version": "cerebrum-transfer007-failure-audit.v1",
        "source_protocol": "CEREBRUM-TRANSFER-007-STAGED-DIAGNOSTIC",
        "status": "EXECUTION_TRANSFER_FAILURE_CONFIRMED" if passed else "AUDIT_INPUT_INCOMPLETE",
        "checks": checks,
        "checks_passed": sum(checks.values()),
        "check_count": len(checks),
        "diagnosis": (
            "Transfer-007 smoke retained partial certificate behavior but failed exact event execution, "
            "decision-clock deferral, state reconstruction, causal comparison, and safe authorization."
        ),
        "repair_requirements": [
            "deferral on every fresh training trajectory",
            "variable decision clocks",
            "executed and deferred events in the same queue",
            "multi-path exact state mutation",
            "upweighted queue and pair-diff supervision",
            "multiple generator profiles and training renderers plus a fresh held-out generator profile",
        ],
        "authorization": "DIAGNOSTIC_ONLY_FRESH_LINEAGE_REPAIR_REQUIRED",
        "binding_authority": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--observed",
        type=Path,
        default=ROOT / "evidence" / "transfer007-observed-result.json",
    )
    parser.add_argument("--output", type=Path, default=ROOT / "results" / "transfer007-failure-audit.json")
    args = parser.parse_args()
    result = audit(json.loads(args.observed.read_text(encoding="utf-8")))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["status"].endswith("CONFIRMED") else 1


if __name__ == "__main__":
    raise SystemExit(main())