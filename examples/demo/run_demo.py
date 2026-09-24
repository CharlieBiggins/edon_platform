#!/usr/bin/env python3
"""Run the complete synthetic EDON platform pipeline."""

from __future__ import annotations

import argparse
import json
import sys
from copy import deepcopy
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from edon.actionnet import generate_actionnet
from edon.cerebrum import TrainingOrchestrator
from edon.compiler import compile_institution
from edon.gaps import discover_gaps
from edon.qualification import qualify_actionnet
from edon.registry import ReviewRegistry
from edon.runtime import InstitutionalRuntime, expected_facts
from edon.shadow import run_shadow_comparison


TIMES = {
    "register": "2026-08-14T05:00:00+00:00",
    "review_1": "2026-08-14T05:01:00+00:00",
    "review_2": "2026-08-14T05:02:00+00:00",
    "promote": "2026-08-14T05:03:00+00:00",
}


def _write(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def run_demo(output_dir: Path) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    compiler_report = compile_institution(ROOT / "examples" / "hospital" / "compiler-input.json")
    _write(output_dir / "compiler-report.json", compiler_report)

    registry = ReviewRegistry(output_dir / "registry.sqlite3")
    candidate_ids = registry.register_compiler_run(compiler_report, timestamp=TIMES["register"])
    promoted: list[str] = []
    for candidate_id in candidate_ids:
        candidate = registry.get_candidate(candidate_id)
        conflict_resolutions = {
            conflict_id: "Normative value retained after synthetic domain review"
            for conflict_id in candidate.get("conflict_ids", [])
        }
        registry.submit_review(
            candidate_id,
            "domain-reviewer",
            "DOMAIN_REVIEWER",
            "APPROVE",
            "Synthetic source and mechanism review completed",
            resolutions=conflict_resolutions,
            timestamp=TIMES["review_1"],
        )
        if candidate["mechanism"]["risk_class"] in {"HIGH", "CRITICAL"}:
            registry.submit_review(
                candidate_id,
                "safety-reviewer",
                "SAFETY_REVIEWER",
                "APPROVE",
                "Independent synthetic safety review completed",
                resolutions=conflict_resolutions,
                timestamp=TIMES["review_2"],
            )
        mechanism = registry.promote(
            candidate_id,
            "release-manager",
            timestamp=TIMES["promote"],
        )
        promoted.append(mechanism["mechanism_id"])

    mechanism = registry.get_mechanism("medication-release")
    runtime = InstitutionalRuntime()
    conforming_state = {"facts": expected_facts(mechanism)}
    allow_certificate = runtime.evaluate(mechanism, conforming_state).as_dict()
    failing_state = deepcopy(conforming_state)
    authority_path = next(path for path in failing_state["facts"] if "authorized_role" in path)
    failing_state["facts"][authority_path] = "unauthorized_actor"
    deny_certificate = runtime.evaluate(mechanism, failing_state).as_dict()
    _write(output_dir / "runtime-certificates.json", {
        "conforming": allow_certificate,
        "failing": deny_certificate,
    })

    actionnet = generate_actionnet(mechanism, generator_seed=26081401)
    qualification = qualify_actionnet(mechanism, actionnet)
    _write(output_dir / "actionnet" / "public-cases.json", actionnet["public"])
    _write(output_dir / "actionnet" / "protected-oracle.json", actionnet["protected"])
    _write(output_dir / "actionnet" / "qualification.json", qualification)

    orchestrator = TrainingOrchestrator(output_dir / "campaigns")
    seeds = [26081411, 26081412]
    campaign = orchestrator.prepare_campaign(
        "CEREBRUM-DEMO-001",
        actionnet,
        qualification,
        seeds,
        condition="REFERENCE_ORACLE_PLUMBING",
        command_template=[sys.executable, "-c", "import sys; print('seed='+sys.argv[1])", "{seed}"],
    )
    launches = orchestrator.launch_seeds(
        "CEREBRUM-DEMO-001",
        campaign["command_template"],
        seeds,
        execute=True,
        timeout_seconds=30,
    )
    evaluations = orchestrator.reference_oracle_diagnostic(actionnet, seeds)
    prediction_manifests = []
    for seed in seeds:
        predictions = [
            {"case_id": case_id, "prediction": label, "oracle_derived": True}
            for case_id, label in sorted(actionnet["protected"]["labels"].items())
        ]
        prediction_manifests.append(
            orchestrator.freeze_predictions("CEREBRUM-DEMO-001", seed, predictions)
        )
    campaign_summary = orchestrator.summarize_gates("CEREBRUM-DEMO-001", evaluations, seeds)

    shadow_records = [{
        "shadow_id": "shadow-unanimous",
        "mechanism_id": "medication-release",
        "context": conforming_state,
        "human_decision": "ALLOW",
        "system_decision": "ALLOW",
        "cerebrum_decision": "ALLOW",
        "runtime_decision": allow_certificate["decision"],
        "runtime_failed_conditions": allow_certificate["failed_conditions"],
    }]
    for index in range(3):
        shadow_records.append({
            "shadow_id": f"shadow-authority-gap-{index}",
            "mechanism_id": "medication-release",
            "context": failing_state,
            "human_decision": "ALLOW",
            "system_decision": "ALLOW",
            "cerebrum_decision": "DENY",
            "runtime_decision": deny_certificate["decision"],
            "runtime_failed_conditions": deny_certificate["failed_conditions"],
        })
    shadow_report = run_shadow_comparison(shadow_records)
    gap_report = discover_gaps(shadow_report, minimum_repetitions=2)
    _write(output_dir / "shadow-report.json", shadow_report)
    _write(output_dir / "gap-proposals.json", gap_report)

    summary = {
        "schema_version": "edon-end-to-end-demo.v1",
        "promoted_mechanisms": sorted(promoted),
        "audit_chain_valid": registry.verify_audit_chain(),
        "runtime": {
            "conforming_decision": allow_certificate["decision"],
            "failing_decision": deny_certificate["decision"],
        },
        "actionnet": {
            "case_count": actionnet["manifest"]["case_count"],
            "qualification_status": qualification["status"],
        },
        "training_orchestration": {
            "campaign_status": campaign["status"],
            "seed_launches_completed": launches["all_completed"],
            "prediction_manifests": prediction_manifests,
            "gate_status": campaign_summary["status"],
            "learning_claim": False,
        },
        "shadow": shadow_report["summary"],
        "gap_proposal_count": gap_report["proposal_count"],
        "binding_authority": False,
        "claim_boundary": "Synthetic end-to-end platform demonstration; no learned, clinical, or production claim.",
    }
    _write(output_dir / "summary.json", summary)
    return summary


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    summary = run_demo(args.output_dir)
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())