#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import random
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parent
EDON_ROOT = ROOT.parents[1]
sys.path.insert(0, str(EDON_ROOT / "src"))

from edon.evaluation.closed_loop_dev import ClosedLoopEnvironment, PROTOCOL_ID


PROFILES = {
    "SERVICE_DESK_OPERATIONS": {
        "domain": "ENTERPRISE_SERVICE_DESK",
        "authority_topology": "HIERARCHICAL_DELEGATION",
        "primary_capability": "TRIAGE_INCIDENT",
        "verification_capability": "VERIFY_RESOLUTION",
        "resource_id": "service_capacity",
        "objective": "Resolve the registered service interruption and verify restoration.",
        "primary_action": "Triage and resolve the registered service interruption.",
        "retry_action": "Repeat triage using the recovery runbook and fresh evidence.",
        "verification_action": "Independently verify that service has been restored.",
        "primary_outcome": "service interruption resolved",
        "verification_outcome": "service restoration independently verified",
    },
    "DISTRIBUTION_CENTER_OPERATIONS": {
        "domain": "WAREHOUSE_FULFILLMENT",
        "authority_topology": "MATRIX_SHIFT_CONTROL",
        "primary_capability": "ROUTE_SHIPMENT",
        "verification_capability": "VERIFY_HANDOFF",
        "resource_id": "handling_capacity",
        "objective": "Recover the delayed shipment and verify its governed handoff.",
        "primary_action": "Route the delayed shipment through an available handling lane.",
        "retry_action": "Reroute the shipment through the registered recovery lane.",
        "verification_action": "Verify custody and completion of the shipment handoff.",
        "primary_outcome": "shipment routed through a feasible lane",
        "verification_outcome": "shipment custody and handoff verified",
    },
    "PERMIT_REVIEW_OPERATIONS": {
        "domain": "ADMINISTRATIVE_PERMIT_REVIEW",
        "authority_topology": "SEQUENTIAL_APPROVAL",
        "primary_capability": "REVIEW_APPLICATION",
        "verification_capability": "VERIFY_RECORD",
        "resource_id": "review_capacity",
        "objective": "Complete the pending permit review and verify the resulting record.",
        "primary_action": "Review the pending application against the registered policy packet.",
        "retry_action": "Repeat review using the corrected evidence packet.",
        "verification_action": "Verify that the review record is complete and internally consistent.",
        "primary_outcome": "permit application review completed",
        "verification_outcome": "permit review record independently verified",
    },
    "CAMPUS_FACILITIES_OPERATIONS": {
        "domain": "CAMPUS_FACILITIES",
        "authority_topology": "ZONE_AND_TRADE_DELEGATION",
        "primary_capability": "DIAGNOSE_FACILITY",
        "verification_capability": "VERIFY_REPAIR",
        "resource_id": "maintenance_capacity",
        "objective": "Restore the affected facility asset and verify safe completion.",
        "primary_action": "Diagnose and restore the affected facility asset.",
        "retry_action": "Repeat restoration using the corrective maintenance procedure.",
        "verification_action": "Independently verify the completed facility restoration.",
        "primary_outcome": "facility asset restored",
        "verification_outcome": "facility restoration independently verified",
    },
}

FAILURES = [
    "The primary outcome lacked the required verification evidence.",
    "The primary action completed against a stale dependency state.",
    "The reported outcome conflicted with the released operational observation.",
    "The primary action exhausted its valid execution window before completion.",
]


def canonical_bytes(value: Any) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n").encode("utf-8")


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(value, handle, indent=2, sort_keys=True, ensure_ascii=False)
        handle.write("\n")


def write_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(canonical_bytes(row).decode("utf-8"))


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256_path(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def pair_classes(counts: dict[str, int]) -> list[str]:
    return [name for name in ("PIVOTAL", "INVARIANCE", "CONTEXTUAL") for _ in range(counts[name])]


def make_episode(
    *,
    split: str,
    pair_index: int,
    pair_class: str,
    variant: str,
    profile_name: str,
    renderer: str,
    scenario_family: str,
    failure_reason: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    profile = PROFILES[profile_name]
    pair_id = f"cld-{split.lower()}-pair-{pair_index:04d}"
    episode_id = f"{pair_id}-{variant.lower()}"
    lineage_id = f"cld-{split.lower()}-{profile_name.lower()}-{pair_index // 12:03d}"
    alias_suffix = "-alias" if pair_class == "INVARIANCE" and variant == "CHANGED" else ""
    contextual_note = (
        "A non-operational staff bulletin was posted for the next quarter."
        if pair_class == "CONTEXTUAL" and variant == "CHANGED"
        else "No unrelated bulletin is active."
    )
    requires_replan = pair_class == "PIVOTAL" and variant == "CHANGED"
    horizon_start = f"2026-09-{3 + (pair_index % 20):02d}T{8 + (pair_index % 8):02d}:00:00+00:00"
    primary_agent = f"agent-primary-{pair_index:04d}"
    verifier_agent = f"agent-verify-{pair_index:04d}"
    episode = {
        "schema_version": "cerebrum-closed-loop-episode.v1",
        "protocol_id": PROTOCOL_ID,
        "split": split,
        "episode_id": episode_id,
        "pair_id": pair_id,
        "pair_class": pair_class,
        "variant": variant,
        "scenario_family": scenario_family,
        "horizon_start": horizon_start,
        "institution": {
            "lineage_id": lineage_id,
            "profile": profile_name,
            "domain": profile["domain"],
            "authority_topology": profile["authority_topology"],
            "renderer": renderer,
        },
        "source_packet": {
            "request": profile["objective"],
            "policy": "Every primary operation requires a separately capable verification step.",
            "authority": "The operations coordinator may propose work; only Kernel may commit a valid transition.",
            "workflow": "Create goal, create feasible plan, dispatch, monitor outcomes, recover if necessary, verify, terminate.",
            "contextual_note": contextual_note,
            "requester_display": f"operations-coordinator{alias_suffix}",
        },
        "objective": profile["objective"],
        "workflow": {
            "primary_action": profile["primary_action"],
            "retry_action": profile["retry_action"],
            "verification_action": profile["verification_action"],
            "primary_capability": profile["primary_capability"],
            "verification_capability": profile["verification_capability"],
            "resource_id": profile["resource_id"],
            "primary_expected_outcome": profile["primary_outcome"],
            "verification_expected_outcome": profile["verification_outcome"],
        },
        "agents": [
            {
                "agent_id": primary_agent,
                "display_name": f"primary-operator{alias_suffix}",
                "capabilities": [profile["primary_capability"]],
                "available": True,
            },
            {
                "agent_id": verifier_agent,
                "display_name": f"verification-operator{alias_suffix}",
                "capabilities": [profile["verification_capability"]],
                "available": True,
            },
            {
                "agent_id": f"agent-ineligible-{pair_index:04d}",
                "display_name": f"archive-operator{alias_suffix}",
                "capabilities": ["ARCHIVE_ONLY"],
                "available": True,
            },
        ],
        "resources": {
            profile["resource_id"]: {"capacity": 2, "available": 2, "unit": "slot"}
        },
        "development_labels_open": split == "TRAIN",
        "training_eligible": split == "TRAIN",
        "protected": False,
        "real_institution": False,
        "binding_authority": False,
    }
    oracle = {
        "schema_version": "cerebrum-closed-loop-oracle.v1",
        "protocol_id": PROTOCOL_ID,
        "episode_id": episode_id,
        "requires_replan": requires_replan,
        "primary_failure_reason": failure_reason,
        "expected_cycle_count": 10 if requires_replan else 8,
        "binding_authority": False,
    }
    return episode, oracle


def generate_split(
    *,
    split: str,
    counts: dict[str, int],
    profiles: list[str],
    renderers: list[str],
    scenarios: list[str],
    rng: random.Random,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    classes = pair_classes(counts)
    rng.shuffle(classes)
    episodes: list[dict[str, Any]] = []
    oracles: list[dict[str, Any]] = []
    for pair_index, pair_class in enumerate(classes):
        profile = profiles[pair_index % len(profiles)]
        renderer = renderers[pair_index % len(renderers)]
        scenario = scenarios[pair_index % len(scenarios)]
        failure = FAILURES[pair_index % len(FAILURES)]
        for variant in ("BASE", "CHANGED"):
            episode, oracle = make_episode(
                split=split,
                pair_index=pair_index,
                pair_class=pair_class,
                variant=variant,
                profile_name=profile,
                renderer=renderer,
                scenario_family=scenario,
                failure_reason=failure,
            )
            episodes.append(episode)
            oracles.append(oracle)
    return episodes, oracles


def materialize_turns(
    episodes: list[dict[str, Any]],
    oracles: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    oracle_by_id = {row["episode_id"]: row for row in oracles}
    training_turns: list[dict[str, Any]] = []
    validation_inputs: list[dict[str, Any]] = []
    validation_labels: list[dict[str, Any]] = []
    run_summaries: list[dict[str, Any]] = []
    for episode in episodes:
        environment = ClosedLoopEnvironment(episode, oracle_by_id[episode["episode_id"]])
        run = environment.run_reference()
        run_summaries.append({key: value for key, value in run.items() if key != "turns"})
        for index, turn in enumerate(run["turns"]):
            record_id = f"turn:{episode['episode_id']}:{index:02d}"
            common = {
                "schema_version": "cerebrum-closed-loop-turn.v1",
                "protocol_id": PROTOCOL_ID,
                "record_id": record_id,
                "episode_id": episode["episode_id"],
                "pair_id": episode["pair_id"],
                "pair_class": episode["pair_class"],
                "cycle_index": index,
                "observation": turn["observation"],
                "binding_authority": False,
            }
            if episode["split"] == "TRAIN":
                training_turns.append(
                    {
                        **common,
                        "target": turn["target"],
                        "training_eligible": True,
                        "sample_weight": 2.0 if episode["pair_class"] == "PIVOTAL" else 1.0,
                    }
                )
            else:
                validation_inputs.append({**common, "training_eligible": False})
                validation_labels.append(
                    {
                        "schema_version": "cerebrum-closed-loop-label.v1",
                        "protocol_id": PROTOCOL_ID,
                        "record_id": record_id,
                        "episode_id": episode["episode_id"],
                        "cycle_index": index,
                        "target": turn["target"],
                        "binding_authority": False,
                    }
                )
    return training_turns, validation_inputs, validation_labels, run_summaries


def build() -> dict[str, Any]:
    design = read_json(ROOT / "config" / "design.json")
    rng = random.Random(design["generator_seed"])
    train_episodes, train_oracles = generate_split(
        split="TRAIN",
        counts=design["split_design"]["train_pair_classes"],
        profiles=design["training_profiles"],
        renderers=design["training_renderers"],
        scenarios=design["scenario_families"],
        rng=rng,
    )
    validation_episodes, validation_oracles = generate_split(
        split="VALIDATION",
        counts=design["split_design"]["validation_pair_classes"],
        profiles=design["heldout_validation_profiles"],
        renderers=design["heldout_validation_renderers"],
        scenarios=design["scenario_families"],
        rng=rng,
    )
    all_episodes = train_episodes + validation_episodes
    all_oracles = train_oracles + validation_oracles
    train_turns, validation_inputs, validation_labels, run_summaries = materialize_turns(all_episodes, all_oracles)

    files = {
        "dataset/train-episodes.jsonl": train_episodes,
        "dataset/train-turns.jsonl": train_turns,
        "dataset/validation-episodes.jsonl": validation_episodes,
        "dataset/validation-inputs.jsonl": validation_inputs,
        "oracle/train-oracle.jsonl": train_oracles,
        "oracle/validation-oracle.jsonl": validation_oracles,
        "oracle/validation-labels.jsonl": validation_labels,
        "results/reference-runs.jsonl": run_summaries,
    }
    for relative, rows in files.items():
        write_jsonl(ROOT / relative, rows)

    hashes = {relative: sha256_path(ROOT / relative) for relative in sorted(files)}
    split_overlap = set(row["episode_id"] for row in train_episodes) & set(row["episode_id"] for row in validation_episodes)
    lineage_overlap = {row["institution"]["lineage_id"] for row in train_episodes} & {
        row["institution"]["lineage_id"] for row in validation_episodes
    }
    validation_label_ids = {row["record_id"] for row in validation_labels}
    validation_input_ids = {row["record_id"] for row in validation_inputs}
    reference_cycles = Counter(row["cycles"] for row in run_summaries)
    controls = {
        "protocol_identity": design["protocol_id"] == PROTOCOL_ID,
        "train_episode_count": len(train_episodes) == design["split_design"]["train_episodes"],
        "validation_episode_count": len(validation_episodes) == design["split_design"]["validation_episodes"],
        "train_pair_count": len({row["pair_id"] for row in train_episodes}) == design["split_design"]["train_pairs"],
        "validation_pair_count": len({row["pair_id"] for row in validation_episodes}) == design["split_design"]["validation_pairs"],
        "train_turn_count": len(train_turns) == 2496,
        "validation_turn_count": len(validation_inputs) == len(validation_labels) == 624,
        "validation_label_alignment": validation_input_ids == validation_label_ids,
        "episode_split_disjoint": not split_overlap,
        "institution_lineage_split_disjoint": not lineage_overlap,
        "profile_split_disjoint": not (set(design["training_profiles"]) & set(design["heldout_validation_profiles"])),
        "renderer_split_disjoint": not (set(design["training_renderers"]) & set(design["heldout_validation_renderers"])),
        "reference_cycle_lengths": set(reference_cycles) == {8, 10},
        "reference_all_success": all(row["episode_success"] for row in run_summaries),
        "reference_zero_kernel_rejections": all(row["kernel_rejections"] == 0 for row in run_summaries),
        "reference_zero_unsafe_proposals": all(row["unsafe_proposals"] == 0 for row in run_summaries),
        "training_rows_eligible": all(row["training_eligible"] is True for row in train_turns),
        "validation_rows_not_training_eligible": all(row["training_eligible"] is False for row in validation_inputs),
        "no_validation_target_in_inputs": all("target" not in row for row in validation_inputs),
        "no_binding_authority": all(row["binding_authority"] is False for row in all_episodes + all_oracles + train_turns + validation_inputs + validation_labels),
        "no_protected_material": all(row["protected"] is False for row in all_episodes),
        "no_real_institution_material": all(row["real_institution"] is False for row in all_episodes),
        "two_candidate_seeds": len(design["candidate_seeds"]) == 2,
        "kernel_only_commit": design["runtime_boundary"]["kernel_only_state_commit"] is True,
        "memory_reset": design["cycle_design"]["memory_reset_between_episodes"] is True,
        "cross_episode_memory_disabled": design["cycle_design"]["cross_episode_memory"] is False,
        "transfer_material_prohibited": design["runtime_boundary"]["protected_transfer_material_allowed"] is False,
        "capstone_material_prohibited": design["runtime_boundary"]["capstone_material_allowed"] is False,
    }
    report = {
        "schema_version": "cerebrum-closed-loop-dev-qualification.v1",
        "protocol_id": PROTOCOL_ID,
        "status": "READY_FOR_TWO_SEED_LEARNED_CLOSED_LOOP_DEVELOPMENT" if all(controls.values()) else "QUALIFICATION_FAILED",
        "control_count": len(controls),
        "controls_passed": sum(controls.values()),
        "controls": controls,
        "counts": {
            "train_episodes": len(train_episodes),
            "train_pairs": len({row["pair_id"] for row in train_episodes}),
            "train_turns": len(train_turns),
            "validation_episodes": len(validation_episodes),
            "validation_pairs": len({row["pair_id"] for row in validation_episodes}),
            "validation_turns": len(validation_inputs),
            "reference_cycle_lengths": dict(sorted(reference_cycles.items())),
        },
        "hashes": hashes,
        "candidate_seeds": design["candidate_seeds"],
        "training_authorized": True,
        "protected_scoring_authorized": False,
        "transfer_claim_authorized": False,
        "igi_claim_authorized": False,
        "binding_authority": False,
        "claim_boundary": "Project-authored synthetic closed-loop development data and executable reference environment only; no learned result, independent transfer, protected capstone, real-institution, production, or IGI claim.",
    }
    write_json(ROOT / "results" / "qualification-report.json", report)

    release = {
        "schema_version": "cerebrum-closed-loop-training-release.v1",
        "release_id": "CEREBRUM-CLOSED-LOOP-DEV-001-TRAINING-v1.0.0",
        "status": "AUTHORIZED_FOR_DEVELOPMENT_TRAINING",
        "created": "2026-09-03",
        "base_model": design["base_model"],
        "candidate_seeds": design["candidate_seeds"],
        "files": [
            {"path": path, "sha256": hashes[path]}
            for path in ("dataset/train-episodes.jsonl", "dataset/train-turns.jsonl", "oracle/train-oracle.jsonl")
        ],
        "source_experiments": ["CEREBRUM-CLOSED-LOOP-DEV-001"],
        "train_episodes": len(train_episodes),
        "train_turns": len(train_turns),
        "all_records_training_eligible": True,
        "protected_labels_included": False,
        "transfer008_material_included": False,
        "capstone_material_included": False,
        "real_institution_data_included": False,
        "training_authorized": True,
        "binding_authority": False,
    }
    write_json(ROOT / "training" / "training-release.json", release)

    manifest = read_json(ROOT / "manifest.json")
    manifest["artifact"]["sha256"] = sha256_path(ROOT / "results" / "qualification-report.json")
    write_json(ROOT / "manifest.json", manifest)
    return report


def main() -> int:
    report = build()
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["status"].startswith("READY_FOR") else 1


if __name__ == "__main__":
    raise SystemExit(main())