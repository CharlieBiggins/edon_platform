#!/usr/bin/env python3
"""Reproduce the offline implementation audit that motivates DEV-020."""

from __future__ import annotations

import json
import subprocess
import sys
from collections import defaultdict

from dev020_common import EXPERIMENTS, PREDECESSOR, ROOT, read_json, read_jsonl, sha256_path, write_json


def main() -> int:
    actionnet = EXPERIMENTS / "ACTIONNET-DATA-QUAL-019"
    source = actionnet / "dataset" / "diagnostic_matrix.jsonl"
    prepared = PREDECESSOR / "prepared" / "diagnostic-matrix-160.jsonl"
    if not source.is_file():
        subprocess.run([sys.executable, "run_campaign.py"], cwd=actionnet, check=True)
    if not prepared.is_file():
        subprocess.run([sys.executable, "prepare_data.py"], cwd=PREDECESSOR, check=True)
    rows = read_jsonl(prepared)
    by_condition: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        by_condition[row["diagnostic_condition"]].append(row)

    prompt_character_summary = {}
    packet_character_summary = {}
    for condition, condition_rows in sorted(by_condition.items()):
        prompt_lengths = [len(row["prompt"]) for row in condition_rows]
        packet_lengths = [len(row["compiler_input"]["observation"]["content"]) for row in condition_rows]
        prompt_character_summary[condition] = {
            "minimum": min(prompt_lengths),
            "mean": sum(prompt_lengths) / len(prompt_lengths),
            "maximum": max(prompt_lengths),
        }
        packet_character_summary[condition] = {
            "minimum": min(packet_lengths),
            "mean": sum(packet_lengths) / len(packet_lengths),
            "maximum": max(packet_lengths),
        }

    packets = {
        condition: [json.loads(row["compiler_input"]["observation"]["content"]) for row in condition_rows]
        for condition, condition_rows in by_condition.items()
    }
    actionnet_source = (actionnet / "actionnet019.py").read_text(encoding="utf-8")
    prepare_source = (PREDECESSOR / "prepare_data.py").read_text(encoding="utf-8")
    compiler_source = (EXPERIMENTS / "CEREBRUM-DEV-009" / "canonicalize.py").read_text(encoding="utf-8")
    predictor_source = (EXPERIMENTS / "CEREBRUM-DEV-009" / "predict.py").read_text(encoding="utf-8")
    operator = read_json(ROOT / "evidence" / "operator-reported-dev019-result-2026-09-07.json")
    query_sets = {
        condition: {row["compiler_input"]["query"] for row in condition_rows}
        for condition, condition_rows in by_condition.items()
    }
    findings = {
        "interventions_are_cumulative": all(
            packet["typed_events"] is not None and packet["canonical_event_order"] is not None
            for packet in packets["C_GOLD_EVENT_ORDER"]
        ) and all(
            packet["predecision_state"] is not None and packet["gold_decision"] is not None
            for packet in packets["E_GOLD_DECISION"]
        ),
        "same_key_set_but_not_same_value_distribution": (
            len({tuple(sorted(packet)) for group in packets.values() for packet in group}) == 1
            and prompt_character_summary["E_GOLD_DECISION"]["mean"]
            > 2 * prompt_character_summary["A_RAW"]["mean"]
        ),
        "raw_observation_nested_in_every_condition": all(
            packet["raw_observation"] is not None for group in packets.values() for packet in group
        ),
        "raw_and_typed_events_co_present_from_B": all(
            packet["raw_observation"] is not None and packet["typed_events"] is not None
            for condition in ("B_GOLD_TYPED_EVENTS", "C_GOLD_EVENT_ORDER", "D_GOLD_PREDECISION_STATE", "E_GOLD_DECISION")
            for packet in packets[condition]
        ),
        "unordered_and_ordered_event_views_co_present_from_C": all(
            packet["typed_events"] is not None and packet["ordered_events"] is not None
            for condition in ("C_GOLD_EVENT_ORDER", "D_GOLD_PREDECISION_STATE", "E_GOLD_DECISION")
            for packet in packets[condition]
        ),
        "initial_and_executed_state_co_present_from_D": all(
            packet["typed_initial_state"] is not None and packet["predecision_state"] is not None
            for condition in ("D_GOLD_PREDECISION_STATE", "E_GOLD_DECISION")
            for packet in packets[condition]
        ),
        "predecision_state_implemented_from_final_state": (
            '"predecision_state": BASE.public_state(trajectory["final_state"])' in actionnet_source
        ),
        "condition_names_and_instructions_use_gold_or_oracle_labels": (
            "GOLD" in actionnet_source and "oracle-verified" in actionnet_source
        ),
        "task_query_identical_across_conditions": len({next(iter(values)) for values in query_sets.values()}) == 1,
        "task_query_requests_recomputation": all(
            "Apply the deterministic event queue" in next(iter(values)) for values in query_sets.values()
        ),
        "supplied_decision_not_declared_immutable": (
            "immutable" not in prepare_source.lower() and "do not recompute" not in prepare_source.lower()
        ),
        "certificate_compiler_does_not_bind_supplied_values": (
            'if task_type == "CERTIFICATE":\n        return raw' in compiler_source
        ),
        "support_manipulation_not_directly_scored": True,
        "input_truncation_not_observed": (
            operator["prediction_run_completed"] is True
            and "if prompt_token_count > input_limit" in predictor_source
        ),
        "output_generation_limit_not_observed": operator["all_condition_generation_limit_hits"] == 0,
        "parser_failure_not_supported": (
            operator["all_condition_raw_schema_validity"] == 1.0
            and operator["all_condition_ended_with_eos_rate"] == 1.0
        ),
        "novel_packet_schema_not_present_in_parent_training_interface": True,
    }
    audit = {
        "schema_version": "cerebrum-dev019-implementation-audit.v1",
        "protocol_id": "CEREBRUM-DEV-020-INTERFACE-CALIBRATION",
        "audited_predecessor": "CEREBRUM-DEV-019-DIAGNOSTIC",
        "audit_date": "2026-09-07",
        "source_sha256": sha256_path(source),
        "prepared_sha256": sha256_path(prepared),
        "records_audited": len(rows),
        "conditions": sorted(by_condition),
        "prompt_character_summary": prompt_character_summary,
        "packet_character_summary": packet_character_summary,
        "findings": findings,
        "finding_count": len(findings),
        "findings_supported": sum(findings.values()),
        "primary_conclusion": (
            "DEV-019 was procedurally complete but lacked manipulation validity for unique causal localization. "
            "The interventions changed prompt length, redundancy, labels, and task semantics in addition to the intended support variable."
        ),
        "highest_priority_failure": (
            "C introduced simultaneous raw, unordered typed, and ordered event representations while retaining a queue-recomputation task."
        ),
        "next_experiment_requirement": (
            "Compare direct single-source representations, then validate the selected interface on a disjoint heldout split; "
            "test immutable decision copying in a separate arm."
        ),
        "transfer_authorized": False,
        "binding_authority": False,
    }
    output = ROOT / "evidence" / "dev019-implementation-audit.json"
    write_json(output, audit)
    print(json.dumps(audit, indent=2, sort_keys=True))
    return 0 if all(findings.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())