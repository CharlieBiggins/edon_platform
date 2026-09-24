#!/usr/bin/env python3
"""Paired recovery analysis for cumulative gold interventions."""

from __future__ import annotations

import json
import math
from collections import Counter, defaultdict
from typing import Any

from dev019_common import canonical


STAGE_LABELS = {
    "B_GOLD_TYPED_EVENTS": "PARSING_OR_TYPED_EVENT_NORMALIZATION",
    "C_GOLD_EVENT_ORDER": "TEMPORAL_ORDERING",
    "D_GOLD_PREDECISION_STATE": "STATE_EXECUTION",
    "E_GOLD_DECISION": "DECISION_POLICY_OR_DECISION_FAITHFULNESS",
    "UNRESOLVED_AFTER_GOLD_DECISION": "CERTIFICATE_GENERATION_OR_UNRESOLVED_MULTISTAGE_FAILURE",
}


def wilson(successes: int, total: int, z: float = 1.959963984540054) -> dict[str, float]:
    if total == 0:
        return {"low": 0.0, "high": 0.0}
    rate = successes / total
    denominator = 1.0 + z * z / total
    center = (rate + z * z / (2.0 * total)) / denominator
    half = z * math.sqrt(rate * (1.0 - rate) / total + z * z / (4.0 * total * total)) / denominator
    return {"low": max(0.0, center - half), "high": min(1.0, center + half)}


def analyze_predictions(
    expected_rows: list[dict[str, Any]],
    predictions: list[dict[str, Any]],
    conditions: list[str],
) -> dict[str, Any]:
    prediction_by_id = {row["case_id"]: row for row in predictions}
    if len(prediction_by_id) != len(predictions):
        raise ValueError("duplicate diagnostic prediction case identifiers")
    evaluations: list[dict[str, Any]] = []
    for row in expected_rows:
        prediction = prediction_by_id.get(row["case_id"])
        if prediction is None:
            raise ValueError(f"missing diagnostic prediction: {row['case_id']}")
        expected = json.loads(row["completion"])
        compiled = prediction.get("compiled") if isinstance(prediction.get("compiled"), dict) else {}
        expected_decision = expected.get("decision")
        actual_decision = compiled.get("decision")
        evaluations.append({
            "case_id": row["case_id"],
            "scenario_id": row["diagnostic_scenario_id"],
            "condition": row["diagnostic_condition"],
            "pair_class": row["pair_class"],
            "variant": row["variant"],
            "mechanism": row.get("pair_mechanism") or row.get("intervention_family") or "NONE",
            "exact": canonical(compiled) == canonical(expected),
            "decision_correct": actual_decision == expected_decision,
            "semantic_state_correct": compiled.get("semantic_state") == expected.get("semantic_state"),
            "raw_schema_valid": prediction.get("raw_schema_valid") is True,
            "ended_with_eos": prediction.get("ended_with_eos") is True,
            "hit_generation_limit": prediction.get("hit_generation_limit") is True,
            "unsafe_authorization": actual_decision == "ALLOW" and expected_decision != "ALLOW",
            "expected_decision": expected_decision,
            "actual_decision": actual_decision,
        })
    by_condition = defaultdict(list)
    by_scenario = defaultdict(dict)
    for row in evaluations:
        by_condition[row["condition"]].append(row)
        by_scenario[row["scenario_id"]][row["condition"]] = row
    condition_results = {}
    for condition in conditions:
        rows = by_condition[condition]
        exact = sum(row["exact"] for row in rows)
        decisions = sum(row["decision_correct"] for row in rows)
        semantic = sum(row["semantic_state_correct"] for row in rows)
        condition_results[condition] = {
            "examples": len(rows),
            "exact": exact,
            "exact_rate": exact / len(rows),
            "exact_rate_wilson_95": wilson(exact, len(rows)),
            "decision_correct": decisions,
            "decision_accuracy": decisions / len(rows),
            "decision_accuracy_wilson_95": wilson(decisions, len(rows)),
            "semantic_state_correct": semantic,
            "semantic_state_accuracy": semantic / len(rows),
            "raw_schema_validity": sum(row["raw_schema_valid"] for row in rows) / len(rows),
            "ended_with_eos_rate": sum(row["ended_with_eos"] for row in rows) / len(rows),
            "generation_limit_hits": sum(row["hit_generation_limit"] for row in rows),
            "unsafe_authorizations": sum(row["unsafe_authorization"] for row in rows),
            "exact_by_mechanism": {
                mechanism: {
                    "correct": sum(row["exact"] for row in rows if row["mechanism"] == mechanism),
                    "total": sum(row["mechanism"] == mechanism for row in rows),
                }
                for mechanism in sorted({row["mechanism"] for row in rows})
            },
        }
    exact_recoveries = Counter()
    decision_recoveries = Counter()
    exact_degradations = Counter()
    decision_degradations = Counter()
    first_exact_recovery = Counter()
    first_decision_recovery = Counter()
    details = []
    for scenario_id, records in sorted(by_scenario.items()):
        if set(records) != set(conditions):
            raise ValueError(f"incomplete condition matrix for {scenario_id}")
        exact_path = [records[condition]["exact"] for condition in conditions]
        decision_path = [records[condition]["decision_correct"] for condition in conditions]
        for before, after in zip(conditions, conditions[1:]):
            if not records[before]["exact"] and records[after]["exact"]:
                exact_recoveries[f"{before}->{after}"] += 1
            if records[before]["exact"] and not records[after]["exact"]:
                exact_degradations[f"{before}->{after}"] += 1
            if not records[before]["decision_correct"] and records[after]["decision_correct"]:
                decision_recoveries[f"{before}->{after}"] += 1
            if records[before]["decision_correct"] and not records[after]["decision_correct"]:
                decision_degradations[f"{before}->{after}"] += 1
        def first_recovery(metric: str) -> str:
            if records[conditions[0]][metric]:
                return "RAW_ALREADY_CORRECT"
            for condition in conditions[1:]:
                if records[condition][metric]:
                    return condition
            return "UNRESOLVED_AFTER_GOLD_DECISION"
        exact_first = first_recovery("exact")
        decision_first = first_recovery("decision_correct")
        first_exact_recovery[exact_first] += 1
        first_decision_recovery[decision_first] += 1
        exemplar = records[conditions[0]]
        details.append({
            "scenario_id": scenario_id,
            "mechanism": exemplar["mechanism"],
            "pair_class": exemplar["pair_class"],
            "variant": exemplar["variant"],
            "exact_path": dict(zip(conditions, exact_path)),
            "decision_path": dict(zip(conditions, decision_path)),
            "first_exact_recovery": exact_first,
            "first_decision_recovery": decision_first,
            "unsafe_conditions": [condition for condition in conditions if records[condition]["unsafe_authorization"]],
        })

    def dominant(counter: Counter) -> dict[str, Any]:
        candidates = {key: value for key, value in counter.items() if key not in {"RAW_ALREADY_CORRECT"} and value > 0}
        if not candidates:
            return {"condition": None, "stage": None, "count": 0, "unique_maximum": False}
        maximum = max(candidates.values())
        winners = sorted(key for key, value in candidates.items() if value == maximum)
        winner = winners[0] if len(winners) == 1 else None
        return {
            "condition": winner,
            "stage": STAGE_LABELS.get(winner) if winner else "MIXED_OR_TIED",
            "count": maximum,
            "unique_maximum": len(winners) == 1,
        }

    return {
        "condition_results": condition_results,
        "paired_transitions": {
            "exact_recoveries": dict(exact_recoveries),
            "exact_degradations": dict(exact_degradations),
            "decision_recoveries": dict(decision_recoveries),
            "decision_degradations": dict(decision_degradations),
        },
        "first_exact_recovery": dict(sorted(first_exact_recovery.items())),
        "first_decision_recovery": dict(sorted(first_decision_recovery.items())),
        "dominant_exact_recovery": dominant(first_exact_recovery),
        "dominant_decision_recovery": dominant(first_decision_recovery),
        "scenario_details": details,
        "unsafe_authorizations_total": sum(row["unsafe_authorization"] for row in evaluations),
        "complete_repeated_measures": len(evaluations) == len(conditions) * len(by_scenario),
    }