#!/usr/bin/env python3
"""Generate and freeze the ACTIONNET-DATA-QUAL-008 authoring package."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from actionnet_multidomain import (
    DATASET_ID,
    DOMAIN_PACKS,
    PIVOTAL_MECHANISMS,
    PROTOCOL_ID,
    RESULT_ID,
    canonical,
    generate,
)
from expert_router import build_review_queue


ROOT = Path(__file__).resolve().parent
DATASET = ROOT / "dataset"
ORACLE = ROOT / "oracle"
LINEAGE = ROOT / "lineage"
RESULTS = ROOT / "results"


def sha(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(canonical(row) + "\n" for row in rows), encoding="utf-8")


def main() -> int:
    generated = generate()
    repeated = generate()
    controls = dict(generated["controls"])
    controls["byte_deterministic_generation"] = canonical(generated) == canonical(repeated)

    authoring_path = DATASET / "authoring_candidates.jsonl"
    validation_path = DATASET / "heldout_authoring_validation.jsonl"
    trajectories_path = ORACLE / "canonical_trajectories.jsonl"
    review_queue_path = ROOT / "expert" / "review_queue.jsonl"
    lineages_path = LINEAGE / "lineages.json"
    reservation_path = ORACLE / "reservation.json"
    mechanism_path = ORACLE / "mechanism_catalog.json"
    coverage_path = ORACLE / "domain_coverage.json"

    write_jsonl(authoring_path, generated["datasets"]["authoring_candidates"])
    write_jsonl(validation_path, generated["datasets"]["heldout_authoring_validation"])
    write_jsonl(trajectories_path, generated["canonical_trajectories"])
    write_jsonl(review_queue_path, build_review_queue(generated["counterfactual_pairs"]))
    write_json(lineages_path, {"schema_version": "actionnet-lineage-registry.v8", "records": generated["lineages"]})
    write_json(reservation_path, generated["protected"])
    write_json(mechanism_path, {
        "schema_version": "actionnet-event-mechanism-catalog.v2",
        "protocol_id": PROTOCOL_ID,
        "pivotal_mechanisms": list(PIVOTAL_MECHANISMS),
        "invariance_mechanism": "QUEUE_ORDER_AND_ACTOR_RENAME",
        "contextual_mechanism": "DECISIVE_CONTEXT_PRESERVATION",
        "scheduler_order": ["time", "priority", "sequence", "event_id"],
        "events_after_disposition_time": "deferred",
        "binding_authority": False,
    })
    write_json(coverage_path, {
        "schema_version": "actionnet-domain-coverage.v1",
        "protocol_id": PROTOCOL_ID,
        "domain_count": len(DOMAIN_PACKS),
        "domains": [
            {
                "domain_id": item["domain_id"],
                "risk_tier": item["risk_tier"],
                "workflow_count": len(item["workflows"]),
                "registered_mechanisms": item["mechanisms"],
                "expert_specialties": item["expert_specialties"],
                "source_grounded": False,
                "expert_review_status": "PENDING",
            }
            for item in DOMAIN_PACKS
        ],
        "coverage_claim": "Broad project-authored sector scaffolding; not exhaustive coverage of all real-world domains or institution-specific policy.",
    })

    data_files = [authoring_path, validation_path, trajectories_path, review_queue_path, lineages_path, reservation_path, mechanism_path, coverage_path]
    counts = {
        "domain_packs": len(DOMAIN_PACKS),
        "executable_pivotal_mechanisms": len(PIVOTAL_MECHANISMS),
        "authoring_candidate_records": len(generated["datasets"]["authoring_candidates"]),
        "heldout_authoring_validation_records": len(generated["datasets"]["heldout_authoring_validation"]),
        "canonical_trajectories": len(generated["canonical_trajectories"]),
        "counterfactual_pairs": len(generated["counterfactual_pairs"]),
        "review_queue_items": len(generated["counterfactual_pairs"]),
        "training_eligible_records": 0,
    }
    dataset_manifest = {
        "schema_version": "actionnet-governed-authoring-dataset-manifest.v8",
        "dataset_id": DATASET_ID,
        "parent_result": "ACTIONNET-DATA-QUAL-007-result-v1.0.0",
        "counts": counts,
        "task_types": ["CERTIFICATE", "TRANSITION", "QUEUE_TRACE", "PAIR_CONTRAST"],
        "files": {path.relative_to(ROOT).as_posix(): sha(path) for path in data_files},
        "source_grounded": False,
        "human_domain_review": False,
        "training_eligible": False,
        "confirmatory_ready": False,
        "public_materialized": False,
        "protected_materialized": False,
        "claim_boundary": "Project-authored synthetic multi-domain candidates for expert authoring and governance workflow development only; not approved Cerebrum training data.",
    }
    write_json(RESULTS / "dataset_manifest.json", dataset_manifest)
    status = "READY_FOR_EXPERT_DOMAIN_AUTHORING" if all(controls.values()) else "HOLD_FOR_REPAIR"
    report = {
        "schema_version": "actionnet-data-qualification-report.v8",
        "result_id": RESULT_ID,
        "status": status,
        "controls": controls,
        "control_count": len(controls),
        "controls_passed": sum(controls.values()),
        "audits": generated["audits"],
        "source_grounded": False,
        "human_domain_review": False,
        "training_eligible": False,
        "independent_generator_implementation": True,
        "binding_authority": False,
        "next_required_gate": "SOURCE_GROUNDING_AND_EXPERT_REVIEW",
        "claim_boundary": "Qualified as an additive multi-domain authoring, routing, and governance scaffold. It does not authorize Cerebrum training, public scoring, autonomous authority, or production use.",
    }
    write_json(RESULTS / "qualification_report.json", report)

    documentation = [ROOT / "README.md", ROOT / "PREREGISTRATION.md", ROOT / "DATA_DESIGN.md", ROOT / "EXPERT_REVIEW_PROTOCOL.md", ROOT / "DOMAIN_EXPANSION_PROTOCOL.md"]
    implementation = [
        ROOT / "actionnet_multidomain.py",
        ROOT / "expert_router.py",
        ROOT / "feedback_pipeline.py",
        ROOT / "governance.py",
        ROOT / "run_campaign.py",
        ROOT / "tests" / "test_multidomain.py",
    ]
    registries = sorted((ROOT / "registry").glob("*.json"))
    contracts = sorted((ROOT / "contracts").glob("*.json")) + sorted((ROOT / "expert").glob("*.schema.json"))
    artifacts = [*documentation, *implementation, *registries, *contracts, RESULTS / "dataset_manifest.json", RESULTS / "qualification_report.json", *data_files]
    manifest = {
        "schema_version": "result-manifest.v1",
        "result_id": RESULT_ID,
        "experiment_id": PROTOCOL_ID,
        "status": status,
        "artifacts": {path.relative_to(ROOT).as_posix(): sha(path) for path in artifacts},
        "claim_boundary": report["claim_boundary"],
    }
    manifest["result_hash"] = "sha256:" + hashlib.sha256(canonical(manifest).encode("utf-8")).hexdigest()
    write_json(RESULTS / "result_manifest.json", manifest)
    checksum_paths = [*data_files, RESULTS / "dataset_manifest.json", RESULTS / "qualification_report.json", RESULTS / "result_manifest.json"]
    (RESULTS / "checksums.sha256").write_text(
        "\n".join(f"{sha(path)[7:]}  {path.relative_to(ROOT).as_posix()}" for path in checksum_paths) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "result_id": RESULT_ID,
        "status": status,
        "controls_passed": sum(controls.values()),
        "control_count": len(controls),
        "counts": counts,
    }, indent=2, sort_keys=True))
    return 0 if status.startswith("READY") else 1


if __name__ == "__main__":
    raise SystemExit(main())