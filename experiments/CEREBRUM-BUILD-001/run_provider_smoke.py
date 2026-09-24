#!/usr/bin/env python3
"""Run one non-binding provider call against a synthetic dispatch context."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent
REPOSITORY = ROOT.parent.parent
sys.path.insert(0, str(REPOSITORY / "src"))

from edon.cerebrum import OperationsProposalAdapter, configured_operations_provider


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    provider, lineage = configured_operations_provider()
    adapter = OperationsProposalAdapter(provider, model_lineage=lineage)
    context = {
        "schema_version": "edon-shadow-supervisor-context.v1",
        "tenant_id": "build-001-smoke",
        "world_id": "synthetic-institution",
        "world_version": 0,
        "world_state_sha256": "sha256:" + "0" * 64,
        "operations": {},
        "alerts": [],
        "ready_steps": [{"plan_id": "plan-smoke", "step_id": "step-smoke"}],
        "assignment_proposals": [{
            "plan_id": "plan-smoke",
            "step_id": "step-smoke",
            "recommended_agent_id": "agent-smoke",
            "dispatchable": True,
        }],
        "mode": "SHADOW",
        "binding_authority": False,
    }
    proposal = adapter.propose(context)
    report = {
        "schema_version": "cerebrum-build-001-provider-smoke.v1",
        "provider": type(provider).__name__,
        "model_lineage": lineage,
        "proposal": proposal,
        "executed": False,
        "binding_authority": False,
        "claim_boundary": "Single synthetic provider plumbing call only; no model-quality claim.",
    }
    rendered = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())