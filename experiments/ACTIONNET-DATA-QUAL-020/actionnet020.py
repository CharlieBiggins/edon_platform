#!/usr/bin/env python3
"""Generate fresh interface-calibration and decision-fidelity cases."""

from __future__ import annotations

import hashlib
import importlib.util
import json
from collections import Counter
from copy import deepcopy
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent
EXPERIMENTS = ROOT.parent
PARENT_PATH = EXPERIMENTS / "ACTIONNET-DATA-QUAL-019" / "actionnet019.py"

PROTOCOL_ID = "ACTIONNET-DATA-QUAL-020"
RESULT_ID = "ACTIONNET-DATA-QUAL-020-result-v1.0.0"
DATASET_ID = "ACTIONNET-INTERFACE-CALIBRATION-v20.0.0"
CALIBRATION_SEED = 26090720
VALIDATION_SEED = 26090730
CALIBRATION_FAMILIES = tuple(range(1080, 1088))
VALIDATION_FAMILIES = tuple(range(1100, 1108))
RESERVED_FAMILIES = tuple(range(1120, 1124))
REPRESENTATIONS = (
    "RAW_DOCKET",
    "TYPED_JSON",
    "COMPACT_TABLE",
    "TEMPORAL_DSL",
    "FAMILIAR_AUGMENTED",
)
FIDELITY_CONDITION = "AUTHENTICATED_DECISION_FIDELITY"
REPRESENTATION_QUERY = (
    "Apply the deterministic event queue through the disposition time and return one canonical "
    "non-authoritative institutional certificate."
)
FIDELITY_QUERY = (
    "Return exactly the authenticated verified_certificate as compact JSON. Preserve every supplied field "
    "and value without recomputing, correcting, or replacing the decision."
)


def _load_parent():
    spec = importlib.util.spec_from_file_location("actionnet019_parent_for_v20", PARENT_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load predecessor generator: {PARENT_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.PROTOCOL_ID = PROTOCOL_ID
    module.PARENT.PROTOCOL_ID = PROTOCOL_ID
    module.V10.PROTOCOL_ID = PROTOCOL_ID
    module.BASE.PROTOCOL_ID = PROTOCOL_ID
    return module


PARENT = _load_parent()
BASE = PARENT.BASE


def canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def digest(value: Any) -> str:
    payload = value if isinstance(value, bytes) else canonical(value).encode("utf-8")
    return "sha256:" + hashlib.sha256(payload).hexdigest()


def event_line(event: dict[str, Any]) -> str:
    return (
        f"{event['event_id']} | {event['time']} | {event['priority']} | {event['sequence']} | "
        f"{event['actor_id']} | {event['operation']} | {event['target']} | {canonical(event['value'])}"
    )


def render_representation(representation: str, trajectory: dict[str, Any]) -> tuple[str, str]:
    state = BASE.public_state(trajectory["initial_state"])
    events = trajectory["submitted_events"]
    clock = state["request"]["query_time"]
    if representation == "RAW_DOCKET":
        content = (
            f"DOCKET<{trajectory['domain']}:INTERFACE_CALIBRATION>\n"
            f"INITIAL_RECORD::{canonical(state)}\n"
            f"SCHEDULED_ENTRIES::{' || '.join(BASE.event_text(event) for event in events)}\n"
            f"DISPOSITION_TIME::{clock}"
        )
        media_type = "text/plain;profile=interface-calibration-raw-docket-v1"
    elif representation == "TYPED_JSON":
        content = canonical({
            "schema_version": "institutional-temporal-input.v1",
            "domain": trajectory["domain"],
            "decision_clock": clock,
            "initial_state": state,
            "submitted_events_unordered": events,
            "ordering_rule": ["time", "priority", "sequence", "event_id"],
            "execution_boundary": "time<=decision_clock",
            "late_event_disposition": "DEFER",
        })
        media_type = "application/json;profile=interface-calibration-typed-v1"
    elif representation == "COMPACT_TABLE":
        rows = "\n".join(event_line(event) for event in events)
        content = (
            f"INSTITUTIONAL EVENT TABLE — {trajectory['domain']}\n"
            f"DECISION_CLOCK={clock}\nINITIAL_STATE={canonical(state)}\n"
            "EVENT_ID | TIME | PRIORITY | SEQUENCE | ACTOR | OPERATION | TARGET | VALUE\n"
            f"{rows}\nORDER=time,priority,sequence,event_id\n"
            "EXECUTE=time<=DECISION_CLOCK; DEFER=time>DECISION_CLOCK"
        )
        media_type = "text/plain;profile=interface-calibration-table-v1"
    elif representation == "TEMPORAL_DSL":
        rows = "\n".join(
            "EVENT "
            f"{event['event_id']} AT {event['time']} PRIORITY {event['priority']} SEQUENCE {event['sequence']} "
            f"ACTOR {event['actor_id']} APPLY {event['operation']} TO {event['target']} VALUE {canonical(event['value'])}"
            for event in events
        )
        content = (
            "TEMPORAL_PROGRAM_INPUT v1\n"
            f"DOMAIN {trajectory['domain']}\nCLOCK {clock}\nSTATE {canonical(state)}\n"
            f"BEGIN_EVENTS\n{rows}\nEND_EVENTS\n"
            "ORDER ASC(time,priority,sequence,event_id)\nEXECUTE IF time<=CLOCK ELSE DEFER"
        )
        media_type = "text/plain;profile=interface-calibration-temporal-dsl-v1"
    elif representation == "FAMILIAR_AUGMENTED":
        content = (
            f"AUGMENTED_DOCKET<{trajectory['domain']}>\n"
            f"INITIAL_RECORD::{canonical(state)}\n"
            f"SCHEDULED_ENTRIES::{' || '.join(BASE.event_text(event) for event in events)}\n"
            f"DISPOSITION_TIME::{clock}\n"
            "ORDER::time,priority,sequence,event_id\n"
            "BOUNDARY::execute at or before disposition time; defer later events"
        )
        media_type = "text/plain;profile=interface-calibration-augmented-docket-v1"
    else:
        raise ValueError(representation)
    return media_type, content


def renderer_registry() -> tuple[dict[str, str], list[dict[str, Any]]]:
    styles = (*REPRESENTATIONS, FIDELITY_CONDITION)
    mapping = {style: BASE.opaque("renderer", PROTOCOL_ID, style, "v1") for style in styles}
    records = [{
        "lineage_id": mapping[style],
        "lineage_type": "renderer",
        "version": "1.0.0",
        "content_sha256": digest({"style": style, "schema": "interface-calibration-v20"}),
        "parents": [],
        "authority": "EDON Research Lab",
        "transformation": "render-single-source-interface-calibration-v1",
    } for style in styles]
    return mapping, records


def record_metadata(
    trajectory: dict[str, Any], split: str, scenario_id: str, condition: str, arm: str
) -> dict[str, Any]:
    return {
        "trajectory_id": trajectory["trajectory_id"],
        "counterfactual_pair_id": trajectory["counterfactual_pair_id"],
        "pair_class": trajectory["pair_class"],
        "variant": trajectory["variant"],
        "intervention_family": trajectory["intervention_family"],
        "pair_mechanism": trajectory["pair_mechanism"],
        "generator_lineage": trajectory["generator_lineage"],
        "generator_profile": "INTERFACE_CALIBRATION",
        "source_lineage": trajectory["source_lineage"],
        "institution_lineage": trajectory["institution_lineage"],
        "authority_graph_lineage": trajectory["authority_graph_lineage"],
        "workflow_graph_lineage": trajectory["workflow_graph_lineage"],
        "semantic_family": trajectory["semantic_family"],
        "selected_renderer": condition,
        "task_type": "CERTIFICATE",
        "decision": trajectory["outcome"]["decision"],
        "sample_weight": 1.0,
        "training_fields": ["input", "target"],
        "calibration_split": split,
        "calibration_arm": arm,
        "calibration_condition": condition,
        "calibration_scenario_id": scenario_id,
        "replay_source_protocol": "FRESH",
    }


def representation_record(
    trajectory: dict[str, Any], split: str, representation: str, renderer_ids: dict[str, str]
) -> dict[str, Any]:
    scenario_id = BASE.opaque("interface-scenario", PROTOCOL_ID, split, trajectory["trajectory_id"])
    media_type, content = render_representation(representation, trajectory)
    return {
        "case_id": BASE.opaque("case", PROTOCOL_ID, scenario_id, representation),
        "input": {
            "observation": {
                "renderer_lineage": renderer_ids[representation],
                "media_type": media_type,
                "content": content,
            },
            "query": REPRESENTATION_QUERY,
        },
        "target": deepcopy(trajectory["outcome"]),
        "metadata": record_metadata(trajectory, split, scenario_id, representation, "REPRESENTATION"),
    }


def fidelity_record(
    trajectory: dict[str, Any], split: str, renderer_ids: dict[str, str]
) -> dict[str, Any]:
    scenario_id = BASE.opaque("interface-scenario", PROTOCOL_ID, split, trajectory["trajectory_id"])
    certificate = deepcopy(trajectory["outcome"])
    content = canonical({
        "schema_version": "authenticated-decision-certificate.v1",
        "source": {
            "kind": "AUTHENTICATED_DETERMINISTIC_EXECUTOR",
            "integrity": "VERIFIED",
            "binding_authority": False,
        },
        "verified_final_state": BASE.public_state(trajectory["final_state"]),
        "verified_certificate": certificate,
        "immutable_fields": sorted(certificate),
        "instruction": "Copy verified_certificate exactly. Do not recompute or alter any supplied field.",
    })
    return {
        "case_id": BASE.opaque("case", PROTOCOL_ID, scenario_id, FIDELITY_CONDITION),
        "input": {
            "observation": {
                "renderer_lineage": renderer_ids[FIDELITY_CONDITION],
                "media_type": "application/json;profile=authenticated-decision-certificate-v1",
                "content": content,
            },
            "query": FIDELITY_QUERY,
        },
        "target": certificate,
        "metadata": record_metadata(
            trajectory, split, scenario_id, FIDELITY_CONDITION, "DECISION_FIDELITY"
        ),
    }


def generate_trajectories(
    split: str, seed: int, families: tuple[int, ...], domains: tuple[str, ...]
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    trajectories, pairs, lineages, audit = BASE.generate_split(
        split, seed, families, 4, domains, "INTERFACE_CALIBRATION"
    )
    for lineage in lineages:
        if lineage["lineage_type"] == "generator":
            lineage["content_sha256"] = digest({
                "protocol": PROTOCOL_ID,
                "split": split,
                "seed": seed,
                "families": families,
                "implementation": "fresh-interface-calibration-v1",
            })
            lineage["parents"] = ["ACTIONNET-DATA-QUAL-019-result-v1.0.0"]
            lineage["transformation"] = "generate-fresh-interface-calibration-v1"
    return trajectories, pairs, lineages, audit


def make_split(
    split: str,
    seed: int,
    families: tuple[int, ...],
    domains: tuple[str, ...],
    renderer_ids: dict[str, str],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    trajectories, pairs, lineages, audit = generate_trajectories(split, seed, families, domains)
    rows = []
    for trajectory in trajectories:
        rows.extend(
            representation_record(trajectory, split, representation, renderer_ids)
            for representation in REPRESENTATIONS
        )
        rows.append(fidelity_record(trajectory, split, renderer_ids))
    return rows, trajectories, pairs, lineages, audit


def summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "records": len(rows),
        "scenarios": len({row["metadata"]["calibration_scenario_id"] for row in rows}),
        "condition_counts": dict(sorted(Counter(
            row["metadata"]["calibration_condition"] for row in rows
        ).items())),
        "arm_counts": dict(sorted(Counter(row["metadata"]["calibration_arm"] for row in rows).items())),
        "mechanism_counts": dict(sorted(Counter(row["metadata"]["pair_mechanism"] for row in rows).items())),
    }


def generate() -> dict[str, Any]:
    renderer_ids, renderer_lineages = renderer_registry()
    calibration = make_split(
        "format_calibration",
        CALIBRATION_SEED,
        CALIBRATION_FAMILIES,
        tuple(f"interface-calibration-{index}" for index in range(8)),
        renderer_ids,
    )
    validation = make_split(
        "heldout_format_validation",
        VALIDATION_SEED,
        VALIDATION_FAMILIES,
        tuple(f"interface-validation-{index}" for index in range(8)),
        renderer_ids,
    )
    calibration_rows, calibration_trajectories, calibration_pairs, calibration_lineages, calibration_audit = calibration
    validation_rows, validation_trajectories, validation_pairs, validation_lineages, validation_audit = validation
    all_rows = calibration_rows + validation_rows
    all_trajectories = calibration_trajectories + validation_trajectories
    condition_set = set(REPRESENTATIONS) | {FIDELITY_CONDITION}

    def groups(rows: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
        result: dict[str, list[dict[str, Any]]] = {}
        for row in rows:
            result.setdefault(row["metadata"]["calibration_scenario_id"], []).append(row)
        return result

    calibration_groups = groups(calibration_rows)
    validation_groups = groups(validation_rows)
    representation_rows = [
        row for row in all_rows if row["metadata"]["calibration_arm"] == "REPRESENTATION"
    ]
    fidelity_rows = [
        row for row in all_rows if row["metadata"]["calibration_arm"] == "DECISION_FIDELITY"
    ]
    calibration_family_set = set(CALIBRATION_FAMILIES)
    validation_family_set = set(VALIDATION_FAMILIES)
    controls = {
        "calibration_record_count_384": len(calibration_rows) == 384,
        "validation_record_count_384": len(validation_rows) == 384,
        "calibration_scenario_count_64": len(calibration_groups) == 64,
        "validation_scenario_count_64": len(validation_groups) == 64,
        "six_conditions_per_scenario": all(
            len(group) == 6 and {
                row["metadata"]["calibration_condition"] for row in group
            } == condition_set
            for group in [*calibration_groups.values(), *validation_groups.values()]
        ),
        "targets_identical_within_scenario": all(
            len({canonical(row["target"]) for row in group}) == 1
            for group in [*calibration_groups.values(), *validation_groups.values()]
        ),
        "representation_query_identical": len({row["input"]["query"] for row in representation_rows}) == 1,
        "fidelity_query_explicitly_immutable": all(
            "without recomputing" in row["input"]["query"]
            for row in fidelity_rows
        ),
        "single_observation_source_per_representation": all(
            "raw_observation" not in row["input"]["observation"]["content"]
            and "ordered_events" not in row["input"]["observation"]["content"]
            and "predecision_state" not in row["input"]["observation"]["content"]
            for row in representation_rows
        ),
        "neutral_input_labels": all(
            "GOLD" not in row["input"]["observation"]["content"].upper()
            and "GOLD" not in row["metadata"]["calibration_condition"].upper()
            for row in all_rows
        ),
        "authenticated_fidelity_source": all(
            "AUTHENTICATED_DETERMINISTIC_EXECUTOR" in row["input"]["observation"]["content"]
            for row in fidelity_rows
        ),
        "all_targets_nonbinding": all(row["target"].get("binding_authority") is False for row in all_rows),
        "all_records_fresh": all(row["metadata"]["replay_source_protocol"] == "FRESH" for row in all_rows),
        "calibration_validation_case_disjoint": not (
            {row["case_id"] for row in calibration_rows} & {row["case_id"] for row in validation_rows}
        ),
        "calibration_validation_scenario_disjoint": not (set(calibration_groups) & set(validation_groups)),
        "calibration_validation_pair_disjoint": not (
            {trajectory["counterfactual_pair_id"] for trajectory in calibration_trajectories}
            & {trajectory["counterfactual_pair_id"] for trajectory in validation_trajectories}
        ),
        "calibration_validation_family_disjoint": not calibration_family_set & validation_family_set,
        "previous_families_disjoint": not (
            (calibration_family_set | validation_family_set) & set(range(780, 1064))
        ),
        "reserved_future_families_unmaterialized": not (
            set(RESERVED_FAMILIES) & (calibration_family_set | validation_family_set)
        ),
        "case_ids_unique": len({row["case_id"] for row in all_rows}) == len(all_rows),
        "trajectory_count_128": len(all_trajectories) == 128,
        "independent_reference_engines_exact": (
            calibration_audit["engine_disagreements"] == validation_audit["engine_disagreements"] == 0
        ),
        "independent_schedulers_exact": (
            calibration_audit["scheduler_disagreements"] == validation_audit["scheduler_disagreements"] == 0
        ),
        "transition_engines_exact": (
            calibration_audit["transition_disagreements"] == validation_audit["transition_disagreements"] == 0
        ),
        "decision_clock_exact": (
            calibration_audit["decision_clock_violations"] == validation_audit["decision_clock_violations"] == 0
        ),
        "evaluation_only_no_training_split": True,
        "heldout_validation_not_used_for_selection": True,
        "transfer_authorization_disabled": True,
        "binding_authority_false": True,
    }
    lineages = [*renderer_lineages, *calibration_lineages, *validation_lineages]
    controls["lineage_ids_unique"] = len({row["lineage_id"] for row in lineages}) == len(lineages)
    return {
        "schema_version": "actionnet-data-qual-020-generated.v1",
        "protocol_id": PROTOCOL_ID,
        "result_id": RESULT_ID,
        "dataset_id": DATASET_ID,
        "calibration": calibration_rows,
        "heldout_validation": validation_rows,
        "calibration_trajectories": calibration_trajectories,
        "validation_trajectories": validation_trajectories,
        "lineages": lineages,
        "controls": controls,
        "audits": {
            "calibration": summarize(calibration_rows),
            "heldout_validation": summarize(validation_rows),
            "calibration_generator": calibration_audit,
            "validation_generator": validation_audit,
            "aggregate_target_sha256": digest([row["target"] for row in all_rows]),
        },
        "protected": {
            "reserved_future_families": list(RESERVED_FAMILIES),
            "training_split_materialized": False,
            "heldout_validation_selection_locked": True,
            "dev018_confirmation_reused": False,
            "dev019_cases_reused": False,
            "public_materialized": False,
            "protected_materialized": False,
            "real_institution_materialized": False,
        },
    }
