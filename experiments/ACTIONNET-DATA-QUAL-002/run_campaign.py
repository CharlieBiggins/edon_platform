#!/usr/bin/env python3
"""Generate and freeze the observable ActionNet development corpus repair."""

from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from pathlib import Path
from typing import Any

from actionnet_repair import DECISIONS, INTERVENTIONS, SEMANTIC_STATES, canonical, digest, generate, split_disjoint


ROOT = Path(__file__).resolve().parent
RESULTS, DATASET, ORACLE, LINEAGE = (ROOT / name for name in ("results", "dataset", "oracle", "lineage"))
RESULT_ID = "ACTIONNET-DATA-QUAL-002-result-v1.0.0"


def sha(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n" for row in rows), encoding="utf-8")


def observability_audit(datasets: dict[str, list[dict[str, Any]]], labels: list[dict[str, Any]]) -> dict[str, Any]:
    public_labels = {row["case_id"]: row["target"] for row in labels}
    conflicts: dict[str, int] = {}
    duplicate_extras: dict[str, int] = {}
    invalid_unobservable = 0
    prompt_hashes: dict[str, set[str]] = defaultdict(set)
    for split, rows in datasets.items():
        groups: dict[str, list[str]] = defaultdict(list)
        duplicates = 0
        for row in rows:
            target = row.get("target") or public_labels[row["case_id"]]
            prompt_hash = digest(row["input"])
            prompt_hashes[split].add(prompt_hash)
            groups[prompt_hash].append(digest(target))
            content = row["input"]["observation"]["content"]
            lowered = content.lower()
            malformed_visible = (
                "malformed-rank" in lowered
                or ('"type":"set_malformed","value":true' in lowered)
                or "set_malformed=true" in lowered
                or "set malformed=true" in lowered
            )
            if target["decision"] == "INVALID" and not malformed_visible:
                invalid_unobservable += 1
        conflict_groups = 0
        for values in groups.values():
            duplicates += max(0, len(values) - 1)
            conflict_groups += int(len(set(values)) > 1)
        conflicts[split] = conflict_groups
        duplicate_extras[split] = duplicates
    split_names = ("train", "development", "public_holdout")
    prompt_disjoint = not any(prompt_hashes[left] & prompt_hashes[right] for i, left in enumerate(split_names) for right in split_names[i + 1 :])
    memo_values_visible = all("=" in row["input"]["observation"]["content"].split("event sequence is", 1)[-1] for row in datasets["public_holdout"])
    model_inputs_id_free = all(set(row["input"]) == {"observation", "query"} for rows in datasets.values() for row in rows)
    return {
        "id_free_conflicting_target_groups": conflicts,
        "id_free_duplicate_extras": duplicate_extras,
        "invalid_targets_without_malformed_observation": invalid_unobservable,
        "id_free_prompt_hashes_split_disjoint": prompt_disjoint,
        "memo_event_values_visible": memo_values_visible,
        "model_inputs_exclude_case_and_institution_ids": model_inputs_id_free,
    }


def main() -> int:
    generated, repeated = generate(), generate()
    datasets, audits = generated["datasets"], generated["audits"]
    split_lineages = generated["split_lineages"]
    counts = {split: len(rows) for split, rows in datasets.items()}
    canonical_rows = generated["canonical_trajectories"]
    observability = observability_audit(datasets, generated["public_labels"])
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
        "all_interventions_covered": set(audits["mechanism_distribution"]) == set(INTERVENTIONS),
        "no_forbidden_model_inputs": audits["forbidden_model_inputs"] == 0,
        "no_label_encoded_identifiers": audits["label_encoded_identifiers"] == 0,
        "no_decision_labels_in_inputs": audits["decision_label_tokens_in_inputs"] == 0,
        "no_exact_duplicate_inputs_with_ids": audits["exact_duplicate_inputs"] == 0,
        "institution_lineages_disjoint": split_disjoint(split_lineages, "institution"),
        "semantic_families_disjoint": split_disjoint(split_lineages, "family"),
        "generator_lineages_disjoint": split_disjoint(split_lineages, "generator"),
        "domains_disjoint": split_disjoint(split_lineages, "domain"),
        "public_renderer_unseen_in_train": set(audits["selected_renderers"]["public_holdout"]).isdisjoint(audits["selected_renderers"]["train"]),
        "public_labels_separate": all(set(row) == {"case_id", "input"} for row in datasets["public_holdout"]),
        "variant_not_perfect_label_proxy": set(audits["variant_decision_distribution"].get("BASE", {})) >= {"ALLOW", "INVALID"} and set(audits["variant_decision_distribution"].get("CHANGED", {})) >= {"ALLOW", "INVALID"},
        "protected_unmaterialized": generated["protected"]["examples"] == 0 and not generated["protected"]["seed_materialized"],
        "canonical_schema_shape": all(set(row) == {"trajectory_id", "institution_lineage", "generator_lineage", "initial_state", "events", "intervention", "final_state", "reference_decision", "paths", "consequences", "certificate", "renderings"} for row in canonical_rows),
        "lineage_schema_shape": all(set(record) == {"lineage_id", "lineage_type", "version", "content_sha256", "parents", "authority", "transformation"} for record in generated["lineages"]),
        "byte_deterministic_generation": canonical(generated["datasets"]) == canonical(repeated["datasets"]),
        "id_free_targets_observable": sum(observability["id_free_conflicting_target_groups"].values()) == 0,
        "invalid_condition_observable": observability["invalid_targets_without_malformed_observation"] == 0,
        "memo_event_values_visible": observability["memo_event_values_visible"],
        "model_inputs_id_free": observability["model_inputs_exclude_case_and_institution_ids"],
        "id_free_prompt_hashes_disjoint": observability["id_free_prompt_hashes_split_disjoint"],
    }

    write_jsonl(DATASET / "train.jsonl", datasets["train"])
    write_jsonl(DATASET / "development.jsonl", datasets["development"])
    write_jsonl(DATASET / "public_holdout_inputs.jsonl", datasets["public_holdout"])
    write_jsonl(ORACLE / "public_holdout_labels.jsonl", generated["public_labels"])
    write_jsonl(ORACLE / "canonical_trajectories.jsonl", canonical_rows)
    write_json(LINEAGE / "lineages.json", {"schema_version": "actionnet-lineage-registry.v2", "records": generated["lineages"]})
    write_json(ORACLE / "protected_reservation.json", generated["protected"])
    dataset_files = [DATASET / "train.jsonl", DATASET / "development.jsonl", DATASET / "public_holdout_inputs.jsonl", ORACLE / "public_holdout_labels.jsonl", ORACLE / "canonical_trajectories.jsonl", LINEAGE / "lineages.json", ORACLE / "protected_reservation.json"]
    write_json(RESULTS / "dataset_manifest.json", {
        "schema_version": "actionnet-development-dataset-manifest.v2",
        "dataset_id": "ACTIONNET-DEV-DATASET-v2.0.0",
        "supersedes_for_model_development": "ACTIONNET-DEV-DATASET-v1.0.0",
        "examples": counts,
        "files": {path.relative_to(ROOT).as_posix(): sha(path) for path in dataset_files},
        "source_grounded": False,
        "confirmatory_ready": False,
        "claim_boundary": "Observable synthetic development corpus only; not real-institution or confirmatory data.",
    })
    status = "READY_FOR_DEVELOPMENT_TRAINING_OBSERVABLE" if all(controls.values()) else "HOLD_FOR_REPAIR"
    report = {
        "schema_version": "actionnet-data-qualification-report.v2",
        "result_id": RESULT_ID,
        "status": status,
        "controls": controls,
        "control_count": len(controls),
        "controls_passed": sum(controls.values()),
        "counts": counts,
        "audits": audits,
        "observability_audit": observability,
        "source_grounded": False,
        "confirmatory_ready": False,
        "human_domain_review": False,
        "independent_generator_implementation": False,
        "claim_boundary": "Qualified for internal development training with observable target factors; no cross-institution or real-institution claim.",
    }
    write_json(RESULTS / "qualification_report.json", report)
    artifacts = [ROOT / "README.md", ROOT / "PREREGISTRATION.md", ROOT / "actionnet_repair.py", ROOT / "run_campaign.py", RESULTS / "dataset_manifest.json", RESULTS / "qualification_report.json"] + dataset_files
    manifest = {"schema_version": "result-manifest.v1", "result_id": RESULT_ID, "experiment_id": "ACTIONNET-DATA-QUAL-002", "status": status, "artifacts": {path.relative_to(ROOT).as_posix(): sha(path) for path in artifacts}, "claim_boundary": report["claim_boundary"]}
    manifest["result_hash"] = "sha256:" + hashlib.sha256(canonical(manifest)).hexdigest()
    write_json(RESULTS / "result_manifest.json", manifest)
    checksum_paths = dataset_files + [RESULTS / "dataset_manifest.json", RESULTS / "qualification_report.json", RESULTS / "result_manifest.json"]
    (RESULTS / "checksums.sha256").write_text("\n".join(f"{sha(path).removeprefix('sha256:')}  {path.relative_to(ROOT).as_posix()}" for path in checksum_paths) + "\n", encoding="utf-8")
    print(json.dumps({"result_id": RESULT_ID, "status": status, "controls_passed": sum(controls.values()), "control_count": len(controls), "observability": observability}, indent=2, sort_keys=True))
    return 0 if status.startswith("READY") else 1


if __name__ == "__main__":
    raise SystemExit(main())