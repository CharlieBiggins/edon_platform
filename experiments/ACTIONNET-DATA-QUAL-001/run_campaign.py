#!/usr/bin/env python3
"""Generate, qualify, and freeze the ActionNet development corpus."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from actionnet import DECISIONS, INTERVENTIONS, SEMANTIC_STATES, canonical, digest, generate, split_disjoint


ROOT = Path(__file__).resolve().parent
RESULTS = ROOT / "results"
DATASET = ROOT / "dataset"
ORACLE = ROOT / "oracle"
LINEAGE = ROOT / "lineage"
RESULT_ID = "ACTIONNET-DATA-QUAL-001-result-v1.0.0"


def sha(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n" for row in rows), encoding="utf-8")


def main() -> int:
    generated = generate()
    repeated = generate()
    datasets = generated["datasets"]
    audits = generated["audits"]
    split_lineages = generated["split_lineages"]
    counts = {split: len(rows) for split, rows in datasets.items()}
    canonical_rows = generated["canonical_trajectories"]

    controls = {
        "registered_counts": counts == {"train": 480, "development": 120, "public_holdout": 120},
        "two_reference_engines_exact": audits["engine_disagreements"] == 0,
        "transitions_exact": audits["transition_disagreements"] == 0,
        "counterfactual_pairs_complete": audits["counterfactual_pairs"] == 360,
        "registered_pair_classes": audits["pair_class_distribution"] == {"PIVOTAL": 240, "INVARIANCE": 60, "CONTEXTUAL": 60},
        "pivotal_pairs_change": audits["pivotal_pair_changes"] == 240,
        "invariance_pairs_preserve": audits["invariance_pair_changes"] == 0,
        "contextual_pairs_preserve": audits["contextual_pair_changes"] == 0,
        "minimal_pair_construction": audits["initial_state_mismatches"] == 0 and audits["nonminimal_pairs"] == 0,
        "invariances_hold": audits["invariance_failures"] == 0 and audits["invariance_checks"] == 1440,
        "all_semantic_states_present": set(audits["semantic_distribution"]) == set(SEMANTIC_STATES),
        "all_decisions_present": set(audits["decision_distribution"]) == set(DECISIONS),
        "all_interventions_covered": set(audits["mechanism_distribution"]) == set(INTERVENTIONS) and min(audits["mechanism_distribution"].values()) > 0,
        "no_forbidden_model_inputs": audits["forbidden_model_inputs"] == 0,
        "no_label_encoded_identifiers": audits["label_encoded_identifiers"] == 0,
        "no_decision_labels_in_inputs": audits["decision_label_tokens_in_inputs"] == 0,
        "no_exact_duplicate_inputs": audits["exact_duplicate_inputs"] == 0,
        "institution_lineages_disjoint": split_disjoint(split_lineages, "institution"),
        "semantic_families_disjoint": split_disjoint(split_lineages, "family"),
        "generator_lineages_disjoint": split_disjoint(split_lineages, "generator"),
        "domains_disjoint": split_disjoint(split_lineages, "domain"),
        "prompt_hashes_disjoint": split_disjoint(split_lineages, "prompt"),
        "public_renderer_unseen_in_train": set(audits["selected_renderers"]["public_holdout"]).isdisjoint(audits["selected_renderers"]["train"]),
        "public_labels_separate": all(set(row) == {"input"} for row in datasets["public_holdout"]) and len(generated["public_labels"]) == 120,
        "variant_not_perfect_label_proxy": set(audits["variant_decision_distribution"].get("BASE", {})) >= {"ALLOW", "INVALID"} and set(audits["variant_decision_distribution"].get("CHANGED", {})) >= {"ALLOW", "INVALID"},
        "protected_unmaterialized": generated["protected"]["examples"] == 0 and not generated["protected"]["seed_materialized"] and not set(generated["protected"]["semantic_families"]) & set().union(*(split_lineages[split]["family"] for split in split_lineages)),
        "canonical_schema_shape": all(
            set(row) == {"trajectory_id", "institution_lineage", "generator_lineage", "initial_state", "events", "intervention", "final_state", "reference_decision", "paths", "consequences", "certificate", "renderings"}
            and set(row["paths"]) == {"authority", "evidence", "workflow", "resource"}
            and set(row["certificate"]) == {"semantics_version", "oracle_agreement", "trace_sha256"}
            and all(set(rendering) == {"renderer_lineage", "media_type", "content_sha256"} for rendering in row["renderings"])
            for row in canonical_rows
        ),
        "lineage_schema_shape": all(set(record) == {"lineage_id", "lineage_type", "version", "content_sha256", "parents", "authority", "transformation"} for record in generated["lineages"]),
        "byte_deterministic_generation": canonical(generated["datasets"]) == canonical(repeated["datasets"]) and canonical(generated["canonical_trajectories"]) == canonical(repeated["canonical_trajectories"]),
    }

    write_jsonl(DATASET / "train.jsonl", datasets["train"])
    write_jsonl(DATASET / "development.jsonl", datasets["development"])
    write_jsonl(DATASET / "public_holdout_inputs.jsonl", datasets["public_holdout"])
    write_jsonl(ORACLE / "public_holdout_labels.jsonl", generated["public_labels"])
    write_jsonl(ORACLE / "canonical_trajectories.jsonl", canonical_rows)
    write_json(LINEAGE / "lineages.json", {"schema_version": "actionnet-lineage-registry.v1", "records": generated["lineages"]})
    write_json(ORACLE / "protected_reservation.json", generated["protected"])

    dataset_files = [
        DATASET / "train.jsonl", DATASET / "development.jsonl", DATASET / "public_holdout_inputs.jsonl",
        ORACLE / "public_holdout_labels.jsonl", ORACLE / "canonical_trajectories.jsonl",
        LINEAGE / "lineages.json", ORACLE / "protected_reservation.json",
    ]
    dataset_manifest = {
        "schema_version": "actionnet-development-dataset-manifest.v1",
        "dataset_id": "ACTIONNET-DEV-DATASET-v1.0.0",
        "examples": counts,
        "counterfactual_pairs": 360,
        "files": {path.relative_to(ROOT).as_posix(): sha(path) for path in dataset_files},
        "source_grounded": False,
        "confirmatory_ready": False,
        "protected_examples": 0,
        "claim_boundary": "Synthetic development corpus generated and verified by package-authored components; not real-institution or confirmatory data.",
    }
    write_json(RESULTS / "dataset_manifest.json", dataset_manifest)

    report = {
        "schema_version": "actionnet-data-qualification-report.v1",
        "result_id": RESULT_ID,
        "status": "READY_FOR_DEVELOPMENT_TRAINING" if all(controls.values()) else "HOLD_FOR_REPAIR",
        "controls": controls,
        "control_count": len(controls),
        "controls_passed": sum(controls.values()),
        "counts": counts,
        "audits": audits,
        "source_grounded": False,
        "confirmatory_ready": False,
        "human_domain_review": False,
        "independent_generator_implementation": False,
        "claim_boundary": "Qualified for internal development LoRA pipeline testing only; not protected learning evidence, cross-institution transfer, or real-institution validity.",
    }
    write_json(RESULTS / "qualification_report.json", report)

    artifacts = [ROOT / "README.md", ROOT / "PREREGISTRATION.md", ROOT / "DATA_CARD.md", ROOT / "DEVELOPMENT_TRAINING_HANDOFF.md", ROOT / "actionnet.py", ROOT / "run_campaign.py", RESULTS / "dataset_manifest.json", RESULTS / "qualification_report.json"] + dataset_files
    manifest = {
        "schema_version": "result-manifest.v1",
        "result_id": RESULT_ID,
        "experiment_id": "ACTIONNET-DATA-QUAL-001",
        "status": report["status"],
        "artifacts": {path.relative_to(ROOT).as_posix(): sha(path) for path in artifacts},
        "claim_boundary": report["claim_boundary"],
    }
    manifest["result_hash"] = "sha256:" + hashlib.sha256(canonical(manifest)).hexdigest()
    write_json(RESULTS / "result_manifest.json", manifest)
    checksum_paths = dataset_files + [RESULTS / "dataset_manifest.json", RESULTS / "qualification_report.json", RESULTS / "result_manifest.json"]
    (RESULTS / "checksums.sha256").write_text("\n".join(f"{sha(path).removeprefix('sha256:')}  {path.relative_to(ROOT).as_posix()}" for path in checksum_paths) + "\n", encoding="utf-8")
    print(json.dumps({"result_id": RESULT_ID, "status": report["status"], "controls_passed": report["controls_passed"], "control_count": report["control_count"], "counts": counts}, indent=2, sort_keys=True))
    return 0 if report["status"] == "READY_FOR_DEVELOPMENT_TRAINING" else 1


if __name__ == "__main__":
    raise SystemExit(main())