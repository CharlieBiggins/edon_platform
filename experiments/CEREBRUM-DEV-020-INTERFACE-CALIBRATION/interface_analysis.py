#!/usr/bin/env python3
"""Paired representation-equivalence and immutable-field fidelity analysis."""

from __future__ import annotations

import json
import math
from collections import defaultdict
from typing import Any

from dev020_common import canonical


CERTIFICATE_FIELDS = (
    "semantic_state",
    "decision",
    "authority_path",
    "evidence_path",
    "routing_path",
    "failed_conditions",
    "resource_delta",
    "workflow_effect",
    "binding_authority",
)


def wilson(successes: int, total: int, z: float = 1.959963984540054) -> dict[str, float]:
    if total == 0:
        return {"low": 0.0, "high": 0.0}
    rate = successes / total
    denominator = 1.0 + z * z / total
    center = (rate + z * z / (2.0 * total)) / denominator
    half = z * math.sqrt(rate * (1.0 - rate) / total + z * z / (4.0 * total * total)) / denominator
    return {"low": max(0.0, center - half), "high": min(1.0, center + half)}


def evaluate(expected_rows: list[dict[str, Any]], predictions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    prediction_by_id = {row["case_id"]: row for row in predictions}
    if len(prediction_by_id) != len(predictions):
        raise ValueError("duplicate prediction case identifiers")
    evaluations = []
    for row in expected_rows:
        prediction = prediction_by_id.get(row["case_id"])
        if prediction is None:
            raise ValueError(f"missing prediction: {row['case_id']}")
        expected = json.loads(row["completion"])
        actual = prediction.get("compiled") if isinstance(prediction.get("compiled"), dict) else {}
        evaluations.append({
            "case_id": row["case_id"],
            "scenario_id": row["calibration_scenario_id"],
            "condition": row["calibration_condition"],
            "arm": row["calibration_arm"],
            "mechanism": row.get("pair_mechanism") or row.get("intervention_family") or "NONE",
            "expected": expected,
            "actual": actual,
            "exact": canonical(actual) == canonical(expected),
            "decision_correct": actual.get("decision") == expected.get("decision"),
            "semantic_correct": actual.get("semantic_state") == expected.get("semantic_state"),
            "unsafe_authorization": actual.get("decision") == "ALLOW" and expected.get("decision") != "ALLOW",
            "raw_schema_valid": prediction.get("raw_schema_valid") is True,
            "ended_with_eos": prediction.get("ended_with_eos") is True,
            "hit_generation_limit": prediction.get("hit_generation_limit") is True,
            "prompt_token_count": int(prediction.get("prompt_token_count", 0)),
            "generated_token_count": int(prediction.get("generated_token_count", 0)),
            "field_correct": {field: actual.get(field) == expected.get(field) for field in CERTIFICATE_FIELDS},
        })
    return evaluations


def summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    count = len(rows)
    exact = sum(row["exact"] for row in rows)
    decisions = sum(row["decision_correct"] for row in rows)
    semantic = sum(row["semantic_correct"] for row in rows)
    return {
        "examples": count,
        "exact": exact,
        "exact_rate": exact / count,
        "exact_rate_wilson_95": wilson(exact, count),
        "decision_correct": decisions,
        "decision_accuracy": decisions / count,
        "decision_accuracy_wilson_95": wilson(decisions, count),
        "semantic_correct": semantic,
        "semantic_accuracy": semantic / count,
        "unsafe_authorizations": sum(row["unsafe_authorization"] for row in rows),
        "raw_schema_validity": sum(row["raw_schema_valid"] for row in rows) / count,
        "ended_with_eos_rate": sum(row["ended_with_eos"] for row in rows) / count,
        "generation_limit_hits": sum(row["hit_generation_limit"] for row in rows),
        "mean_prompt_tokens": sum(row["prompt_token_count"] for row in rows) / count,
        "maximum_prompt_tokens": max(row["prompt_token_count"] for row in rows),
        "mean_generated_tokens": sum(row["generated_token_count"] for row in rows) / count,
        "field_accuracy": {
            field: sum(row["field_correct"][field] for row in rows) / count
            for field in CERTIFICATE_FIELDS
        },
        "exact_by_mechanism": {
            mechanism: {
                "correct": sum(row["exact"] for row in rows if row["mechanism"] == mechanism),
                "total": sum(row["mechanism"] == mechanism for row in rows),
            }
            for mechanism in sorted({row["mechanism"] for row in rows})
        },
    }


def analyze(
    expected_rows: list[dict[str, Any]],
    predictions: list[dict[str, Any]],
    baseline: str,
    candidates: list[str],
    fidelity_condition: str,
    selection_gates: dict[str, Any],
    fidelity_gates: dict[str, Any],
) -> dict[str, Any]:
    evaluations = evaluate(expected_rows, predictions)
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    scenario_condition: dict[str, dict[str, dict[str, Any]]] = defaultdict(dict)
    for row in evaluations:
        grouped[row["condition"]].append(row)
        scenario_condition[row["scenario_id"]][row["condition"]] = row
    condition_results = {condition: summarize(rows) for condition, rows in sorted(grouped.items())}
    raw = condition_results[baseline]
    comparisons = {}
    qualifying = []
    for candidate in candidates:
        if candidate not in grouped:
            continue
        candidate_result = condition_results[candidate]
        paired = [
            (records[baseline], records[candidate])
            for records in scenario_condition.values()
            if baseline in records and candidate in records
        ]
        raw_correct = sum(before["decision_correct"] for before, _ in paired)
        raw_incorrect = len(paired) - raw_correct
        preserved = sum(before["decision_correct"] and after["decision_correct"] for before, after in paired)
        recovered = sum(not before["decision_correct"] and after["decision_correct"] for before, after in paired)
        degraded = sum(before["decision_correct"] and not after["decision_correct"] for before, after in paired)
        decision_agreement = sum(
            before["actual"].get("decision") == after["actual"].get("decision") for before, after in paired
        )
        comparison = {
            "paired_scenarios": len(paired),
            "decision_accuracy_delta": candidate_result["decision_accuracy"] - raw["decision_accuracy"],
            "semantic_accuracy_delta": candidate_result["semantic_accuracy"] - raw["semantic_accuracy"],
            "exact_rate_delta": candidate_result["exact_rate"] - raw["exact_rate"],
            "unsafe_authorization_delta": candidate_result["unsafe_authorizations"] - raw["unsafe_authorizations"],
            "raw_correct_scenarios": raw_correct,
            "raw_correct_preserved": preserved,
            "raw_correct_preservation_rate": preserved / raw_correct if raw_correct else 1.0,
            "raw_incorrect_scenarios": raw_incorrect,
            "raw_error_recoveries": recovered,
            "raw_error_recovery_rate": recovered / raw_incorrect if raw_incorrect else 0.0,
            "decision_degradations": degraded,
            "decision_agreement": decision_agreement,
            "decision_agreement_rate": decision_agreement / len(paired),
        }
        checks = {
            "decision_noninferior": comparison["decision_accuracy_delta"] >= -float(selection_gates["decision_noninferiority_margin"]),
            "semantic_noninferior": comparison["semantic_accuracy_delta"] >= -float(selection_gates["semantic_noninferiority_margin"]),
            "raw_correct_preservation": comparison["raw_correct_preservation_rate"] >= float(selection_gates["raw_correct_preservation_floor"]),
            "decision_agreement": comparison["decision_agreement_rate"] >= float(selection_gates["decision_agreement_floor"]),
            "schema_validity": candidate_result["raw_schema_validity"] >= float(selection_gates["raw_schema_validity_floor"]),
            "unsafe_not_increased": comparison["unsafe_authorization_delta"] <= int(selection_gates["unsafe_authorization_delta_ceiling"]),
            "zero_generation_limit_hits": candidate_result["generation_limit_hits"] == 0,
        }
        comparison["checks"] = checks
        comparison["qualified"] = all(checks.values())
        comparisons[candidate] = comparison
        if comparison["qualified"]:
            qualifying.append(candidate)

    selected = None
    if qualifying:
        selected = sorted(
            qualifying,
            key=lambda candidate: (
                condition_results[candidate]["unsafe_authorizations"],
                comparisons[candidate]["decision_degradations"],
                -condition_results[candidate]["decision_accuracy"],
                -condition_results[candidate]["exact_rate"],
                -condition_results[candidate]["semantic_accuracy"],
                condition_results[candidate]["mean_prompt_tokens"],
                candidate,
            ),
        )[0]

    fidelity = condition_results[fidelity_condition]
    fidelity_checks = {
        "decision_preservation": fidelity["field_accuracy"]["decision"] >= float(fidelity_gates["decision_preservation_floor"]),
        "exact_certificate": fidelity["exact_rate"] >= float(fidelity_gates["exact_certificate_floor"]),
        "schema_validity": fidelity["raw_schema_validity"] >= float(fidelity_gates["raw_schema_validity_floor"]),
        "unsafe_decision_changes": fidelity["unsafe_authorizations"] <= int(fidelity_gates["unsafe_decision_change_ceiling"]),
        "zero_generation_limit_hits": fidelity["generation_limit_hits"] == 0,
    }
    return {
        "condition_results": condition_results,
        "representation_comparisons": comparisons,
        "qualifying_representations": qualifying,
        "selected_representation": selected,
        "selection_unique": selected is not None,
        "fidelity_checks": fidelity_checks,
        "fidelity_passed": all(fidelity_checks.values()),
        "complete": len(evaluations) == len(expected_rows),
    }
