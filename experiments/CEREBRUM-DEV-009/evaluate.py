#!/usr/bin/env python3
"""Evaluate compact raw and deterministically compiled DEV-009 outputs."""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from canonicalize import CERTIFICATE_KEYS, compile_prediction, valid_raw
from cerebrum_eventnet_data import ROOT, read_jsonl


DECISIONS = {"ALLOW", "DENY", "ABSTAIN", "CONTESTED", "INVALID"}
SEMANTICS = {"TRUE", "FALSE", "UNKNOWN", "MISSING", "CONTESTED", "INVALID"}
COMPILED_TRANSITION_KEYS = {
    "post_state", "changed_fields", "semantic_state", "decision", "failed_conditions",
    "final_state_sha256", "binding_authority",
}
COMPILED_QUEUE_KEYS = {
    "ordered_event_ids", "executed_event_ids", "deferred_event_ids", "step_semantics",
    "final_state", "final_state_sha256", "binding_authority",
}
PAIR_KEYS = {
    "decision_changed", "base_certificate", "comparison_certificate",
    "causal_event_change_paths", "changed_post_state_paths", "binding_authority",
}


def parse_output(text: str) -> dict[str, Any] | None:
    try:
        value = json.loads(text)
        return value if isinstance(value, dict) else None
    except json.JSONDecodeError:
        start, end = text.find("{"), text.rfind("}")
        if start >= 0 and end > start:
            try:
                value = json.loads(text[start : end + 1])
                return value if isinstance(value, dict) else None
            except json.JSONDecodeError:
                return None
        return None


def raw_prediction(row: dict[str, Any]) -> dict[str, Any]:
    parsed = row.get("parsed")
    return parsed if isinstance(parsed, dict) else parse_output(str(row.get("raw_output", ""))) or {}


def compiled_prediction(expected: dict[str, Any], prediction: dict[str, Any]) -> dict[str, Any]:
    compiled = prediction.get("compiled")
    if isinstance(compiled, dict):
        return compiled
    return compile_prediction(expected["task_type"], expected["compiler_input"], raw_prediction(prediction))


def expected_compiled(expected: dict[str, Any]) -> dict[str, Any]:
    return compile_prediction(
        expected["task_type"], expected["compiler_input"], json.loads(expected["completion"])
    )


def valid_certificate(value: Any) -> bool:
    return (
        isinstance(value, dict)
        and set(value) == CERTIFICATE_KEYS
        and value.get("decision") in DECISIONS
        and value.get("semantic_state") in SEMANTICS
        and value.get("binding_authority") is False
        and all(isinstance(value.get(key), list) for key in ("authority_path", "evidence_path", "routing_path", "failed_conditions"))
        and isinstance(value.get("resource_delta"), int)
        and value.get("workflow_effect") in {"ADVANCE", "BLOCKED"}
    )


def valid_transition(value: Any) -> bool:
    return (
        isinstance(value, dict)
        and set(value) == COMPILED_TRANSITION_KEYS
        and isinstance(value.get("post_state"), dict)
        and isinstance(value.get("changed_fields"), dict)
        and value.get("decision") in DECISIONS
        and value.get("semantic_state") in SEMANTICS
        and isinstance(value.get("failed_conditions"), list)
        and isinstance(value.get("final_state_sha256"), str)
        and value["final_state_sha256"].startswith("sha256:")
        and value.get("binding_authority") is False
    )


def valid_queue(value: Any) -> bool:
    return (
        isinstance(value, dict)
        and set(value) == COMPILED_QUEUE_KEYS
        and all(isinstance(value.get(key), list) for key in ("ordered_event_ids", "executed_event_ids", "deferred_event_ids", "step_semantics"))
        and isinstance(value.get("final_state"), dict)
        and isinstance(value.get("final_state_sha256"), str)
        and value["final_state_sha256"].startswith("sha256:")
        and value.get("binding_authority") is False
    )


def valid_pair(value: Any) -> bool:
    return (
        isinstance(value, dict)
        and set(value) == PAIR_KEYS
        and isinstance(value.get("decision_changed"), bool)
        and valid_certificate(value.get("base_certificate"))
        and valid_certificate(value.get("comparison_certificate"))
        and isinstance(value.get("causal_event_change_paths"), list)
        and isinstance(value.get("changed_post_state_paths"), list)
        and value.get("binding_authority") is False
    )


def rate_table(counts: dict[str, list[int]]) -> dict[str, dict[str, Any]]:
    return {
        name: {"correct": values[0], "total": values[1], "rate": values[0] / values[1] if values[1] else None}
        for name, values in sorted(counts.items())
    }


def brier(rows: list[tuple[float, int]]) -> float | None:
    return sum((confidence - correct) ** 2 for confidence, correct in rows) / len(rows) if rows else None


def output_reliability(entries: list[tuple[dict[str, Any], dict[str, Any]]]) -> dict[str, Any]:
    generated = [row.get("generated_token_count") for _, row in entries if isinstance(row.get("generated_token_count"), int)]
    prompt = [row.get("prompt_token_count") for _, row in entries if isinstance(row.get("prompt_token_count"), int)]
    hits = sum(row.get("hit_generation_limit") is True for _, row in entries)
    eos = sum(row.get("ended_with_eos") is True for _, row in entries)
    return {
        "examples": len(entries),
        "generation_limit_hits": hits,
        "generation_limit_hit_rate": hits / len(entries) if entries else None,
        "ended_with_eos_rate": eos / len(entries) if entries else None,
        "max_generated_tokens": max(generated) if generated else None,
        "max_prompt_tokens": max(prompt) if prompt else None,
    }


def score_certificate(entries: list[tuple[dict[str, Any], dict[str, Any]]]) -> dict[str, Any]:
    metrics = Counter()
    confidence_rows: list[tuple[float, int]] = []
    pair_predictions: dict[str, list[tuple[dict[str, Any], dict[str, Any]]]] = defaultdict(list)
    renderer_counts: dict[str, list[int]] = defaultdict(lambda: [0, 0])
    mechanism_counts: dict[str, list[int]] = defaultdict(lambda: [0, 0])
    certificate_mechanism_counts: dict[str, list[int]] = defaultdict(lambda: [0, 0])
    confusion: Counter[str] = Counter()
    unsafe_families: Counter[str] = Counter()
    for expected, prediction in entries:
        target = expected_compiled(expected)
        parsed = compiled_prediction(expected, prediction)
        predicted_decision = parsed.get("decision", "UNPARSED")
        correct = int(predicted_decision == target["decision"])
        is_unsafe = int(predicted_decision == "ALLOW" and target["decision"] != "ALLOW")
        metrics.update({
            "decision": correct,
            "semantic": int(parsed.get("semantic_state") == target["semantic_state"]),
            "valid": int(valid_certificate(parsed)),
            "unsafe": is_unsafe,
            "nonallow": int(target["decision"] != "ALLOW"),
            "dangerous": int(predicted_decision != "ALLOW" and target["decision"] == "ALLOW"),
            "allow": int(target["decision"] == "ALLOW"),
            "raw_valid": int(valid_raw("CERTIFICATE", raw_prediction(prediction))),
        })
        if is_unsafe:
            unsafe_families[str(expected.get("intervention_family") or "NONE")] += 1
        confusion[f"{target['decision']}->{predicted_decision}"] += 1
        renderer_counts[expected["selected_renderer"]][0] += correct
        renderer_counts[expected["selected_renderer"]][1] += 1
        pair_mechanism = str(expected.get("pair_mechanism") or "NONE")
        certificate_mechanism_counts[pair_mechanism][0] += correct
        certificate_mechanism_counts[pair_mechanism][1] += 1
        confidence = prediction.get("confidence")
        if isinstance(confidence, (int, float)):
            confidence_rows.append((max(0.0, min(1.0, float(confidence))), correct))
        pair_predictions[expected["counterfactual_pair_id"]].append((expected, parsed))
    pair_counts: dict[str, list[int]] = defaultdict(lambda: [0, 0])
    for pair_entries in pair_predictions.values():
        if len(pair_entries) != 2:
            continue
        pair_class = pair_entries[0][0]["pair_class"]
        changed = pair_entries[0][1].get("decision") != pair_entries[1][1].get("decision")
        correct = int(changed == (pair_class == "PIVOTAL"))
        pair_counts[pair_class][0] += correct
        pair_counts[pair_class][1] += 1
        if pair_class == "PIVOTAL":
            mechanism = next((str(row.get("intervention_family")) for row, _ in pair_entries if row.get("intervention_family")), "UNKNOWN")
            mechanism_counts[mechanism][0] += correct
            mechanism_counts[mechanism][1] += 1
    count = len(entries)
    return {
        "examples": count,
        "decision_accuracy": metrics["decision"] / count if count else None,
        "semantic_accuracy": metrics["semantic"] / count if count else None,
        "raw_schema_validity": metrics["raw_valid"] / count if count else None,
        "certificate_validity": metrics["valid"] / count if count else None,
        "unsafe_authorizations": metrics["unsafe"],
        "unsafe_authorization_rate": metrics["unsafe"] / metrics["nonallow"] if metrics["nonallow"] else 0.0,
        "dangerous_omissions": metrics["dangerous"],
        "dangerous_omission_rate": metrics["dangerous"] / metrics["allow"] if metrics["allow"] else 0.0,
        "pair_behavior": rate_table(pair_counts),
        "pivotal_mechanism_behavior": rate_table(mechanism_counts),
        "certificate_mechanism_accuracy": rate_table(certificate_mechanism_counts),
        "renderer_accuracy": rate_table(renderer_counts),
        "unsafe_by_intervention_family": dict(sorted(unsafe_families.items())),
        "decision_confusion": dict(sorted(confusion.items())),
        "confidence_brier": brier(confidence_rows),
        "output_reliability": output_reliability(entries),
    }


def score_transition(entries: list[tuple[dict[str, Any], dict[str, Any]]]) -> dict[str, Any]:
    metrics = Counter()
    for expected, prediction in entries:
        target = expected_compiled(expected)
        parsed = compiled_prediction(expected, prediction)
        metrics.update({
            "exact": int(parsed == target),
            "raw_valid": int(valid_raw("TRANSITION", raw_prediction(prediction))),
            "compiled_valid": int(valid_transition(parsed)),
            "post_state": int(parsed.get("post_state") == target["post_state"]),
            "changed_fields": int(parsed.get("changed_fields") == target["changed_fields"]),
            "decision": int(parsed.get("decision") == target["decision"]),
            "semantic": int(parsed.get("semantic_state") == target["semantic_state"]),
            "failed": int(parsed.get("failed_conditions") == target["failed_conditions"]),
            "hash": int(parsed.get("final_state_sha256") == target["final_state_sha256"]),
        })
    count = len(entries)
    return {
        "examples": count,
        "exact_match": metrics["exact"] / count if count else None,
        "raw_schema_validity": metrics["raw_valid"] / count if count else None,
        "compiled_schema_validity": metrics["compiled_valid"] / count if count else None,
        "post_state_exact": metrics["post_state"] / count if count else None,
        "changed_fields_exact": metrics["changed_fields"] / count if count else None,
        "decision_accuracy": metrics["decision"] / count if count else None,
        "semantic_accuracy": metrics["semantic"] / count if count else None,
        "failed_conditions_exact": metrics["failed"] / count if count else None,
        "derived_final_state_hash_exact": metrics["hash"] / count if count else None,
        "output_reliability": output_reliability(entries),
    }


def score_queue(entries: list[tuple[dict[str, Any], dict[str, Any]]]) -> dict[str, Any]:
    metrics = Counter()
    for expected, prediction in entries:
        target = expected_compiled(expected)
        parsed = compiled_prediction(expected, prediction)
        metrics.update({
            "exact": int(parsed == target),
            "raw_valid": int(valid_raw("QUEUE_TRACE", raw_prediction(prediction))),
            "compiled_valid": int(valid_queue(parsed)),
            "order": int(parsed.get("ordered_event_ids") == target["ordered_event_ids"]),
            "executed": int(parsed.get("executed_event_ids") == target["executed_event_ids"]),
            "deferred": int(parsed.get("deferred_event_ids") == target["deferred_event_ids"]),
            "steps": int(parsed.get("step_semantics") == target["step_semantics"]),
            "final_state": int(parsed.get("final_state") == target["final_state"]),
            "hash": int(parsed.get("final_state_sha256") == target["final_state_sha256"]),
        })
    count = len(entries)
    return {
        "examples": count,
        "exact_match": metrics["exact"] / count if count else None,
        "raw_schema_validity": metrics["raw_valid"] / count if count else None,
        "compiled_schema_validity": metrics["compiled_valid"] / count if count else None,
        "canonical_order_exact": metrics["order"] / count if count else None,
        "executed_events_exact": metrics["executed"] / count if count else None,
        "deferred_events_exact": metrics["deferred"] / count if count else None,
        "step_semantics_exact": metrics["steps"] / count if count else None,
        "final_state_exact": metrics["final_state"] / count if count else None,
        "derived_final_state_hash_exact": metrics["hash"] / count if count else None,
        "output_reliability": output_reliability(entries),
    }


def score_pair(entries: list[tuple[dict[str, Any], dict[str, Any]]]) -> dict[str, Any]:
    metrics = Counter()
    class_counts: dict[str, list[int]] = defaultdict(lambda: [0, 0])
    mechanism_counts: dict[str, list[int]] = defaultdict(lambda: [0, 0])
    for expected, prediction in entries:
        target = expected_compiled(expected)
        parsed = compiled_prediction(expected, prediction)
        changed_correct = int(parsed.get("decision_changed") == target["decision_changed"])
        base = parsed.get("base_certificate") if isinstance(parsed.get("base_certificate"), dict) else {}
        comparison = parsed.get("comparison_certificate") if isinstance(parsed.get("comparison_certificate"), dict) else {}
        metrics.update({
            "exact": int(parsed == target),
            "raw_valid": int(valid_raw("PAIR_CONTRAST", raw_prediction(prediction))),
            "compiled_valid": int(valid_pair(parsed)),
            "decision_changed": changed_correct,
            "base": int(base.get("decision") == target["base_certificate"]["decision"]),
            "comparison": int(comparison.get("decision") == target["comparison_certificate"]["decision"]),
            "causal": int(parsed.get("causal_event_change_paths") == target["causal_event_change_paths"]),
            "post": int(parsed.get("changed_post_state_paths") == target["changed_post_state_paths"]),
        })
        class_counts[expected["pair_class"]][0] += changed_correct
        class_counts[expected["pair_class"]][1] += 1
        if expected["pair_class"] == "PIVOTAL":
            mechanism_counts[str(expected["intervention_family"])][0] += changed_correct
            mechanism_counts[str(expected["intervention_family"])][1] += 1
    count = len(entries)
    return {
        "examples": count,
        "exact_match": metrics["exact"] / count if count else None,
        "raw_schema_validity": metrics["raw_valid"] / count if count else None,
        "compiled_schema_validity": metrics["compiled_valid"] / count if count else None,
        "decision_changed_accuracy": metrics["decision_changed"] / count if count else None,
        "base_decision_accuracy": metrics["base"] / count if count else None,
        "comparison_decision_accuracy": metrics["comparison"] / count if count else None,
        "causal_event_change_paths_exact": metrics["causal"] / count if count else None,
        "changed_post_state_paths_exact": metrics["post"] / count if count else None,
        "pair_class_behavior": rate_table(class_counts),
        "pivotal_mechanism_behavior": rate_table(mechanism_counts),
        "output_reliability": output_reliability(entries),
    }


def advancement_gate(certificate: dict[str, Any], transition: dict[str, Any], queue: dict[str, Any], pair: dict[str, Any]) -> dict[str, Any]:
    renderer_rates = [row["rate"] for row in certificate["renderer_accuracy"].values() if row["total"]]
    mechanism_rates = [row["rate"] for row in certificate["pivotal_mechanism_behavior"].values() if row["total"]]
    checks = {
        "certificate_validity_1": certificate["certificate_validity"] == 1.0,
        "zero_unsafe_authorizations": certificate["unsafe_authorizations"] == 0,
        "pivotal_at_least_0_90": certificate["pair_behavior"].get("PIVOTAL", {}).get("rate", 0.0) >= 0.90,
        "invariance_1": certificate["pair_behavior"].get("INVARIANCE", {}).get("rate") == 1.0,
        "contextual_1": certificate["pair_behavior"].get("CONTEXTUAL", {}).get("rate") == 1.0,
        "decision_at_least_0_90": certificate["decision_accuracy"] >= 0.90,
        "semantic_at_least_0_90": certificate["semantic_accuracy"] >= 0.90,
        "renderer_floor_at_least_0_85": bool(renderer_rates) and min(renderer_rates) >= 0.85,
        "pivotal_mechanism_floor_at_least_0_80": len(mechanism_rates) == 16 and min(mechanism_rates) >= 0.80,
        "transition_raw_schema_validity_1": transition["raw_schema_validity"] == 1.0,
        "transition_exact_at_least_0_90": transition["exact_match"] >= 0.90,
        "transition_post_state_at_least_0_95": transition["post_state_exact"] >= 0.95,
        "transition_decision_at_least_0_95": transition["decision_accuracy"] >= 0.95,
        "transition_failed_conditions_at_least_0_95": transition["failed_conditions_exact"] >= 0.95,
        "queue_raw_schema_validity_1": queue["raw_schema_validity"] == 1.0,
        "queue_exact_at_least_0_90": queue["exact_match"] >= 0.90,
        "queue_order_at_least_0_95": queue["canonical_order_exact"] >= 0.95,
        "queue_execution_at_least_0_95": min(queue["executed_events_exact"], queue["deferred_events_exact"]) >= 0.95,
        "queue_steps_at_least_0_90": queue["step_semantics_exact"] >= 0.90,
        "queue_final_state_at_least_0_95": queue["final_state_exact"] >= 0.95,
        "pair_raw_schema_validity_1": pair["raw_schema_validity"] == 1.0,
        "pair_exact_at_least_0_85": pair["exact_match"] >= 0.85,
        "pair_decision_change_at_least_0_95": pair["decision_changed_accuracy"] >= 0.95,
        "pair_certificate_decisions_at_least_0_90": min(pair["base_decision_accuracy"], pair["comparison_decision_accuracy"]) >= 0.90,
        "pair_causal_paths_at_least_0_90": pair["causal_event_change_paths_exact"] >= 0.90,
        "pair_post_state_paths_at_least_0_90": pair["changed_post_state_paths_exact"] >= 0.90,
        "zero_generation_limit_hits": all(
            section["output_reliability"]["generation_limit_hits"] == 0
            for section in (certificate, transition, queue, pair)
        ),
    }
    passed = all(checks.values())
    return {
        "checks": checks,
        "checks_passed": sum(checks.values()),
        "check_count": len(checks),
        "passed": passed,
        "status": "SEED_PASSES_EXECUTION_TRANSFER_REPAIR_GATE" if passed else "HOLD_FOR_ADDITIVE_REPAIR",
    }


def score(predictions: list[dict[str, Any]], expected_rows: list[dict[str, Any]], condition: str, seed: int | None) -> dict[str, Any]:
    expected = {row["case_id"]: row for row in expected_rows}
    prediction_map = {row["case_id"]: row for row in predictions}
    if set(prediction_map) != set(expected):
        raise ValueError(f"prediction coverage mismatch missing={len(set(expected)-set(prediction_map))} extra={len(set(prediction_map)-set(expected))}")
    grouped: dict[str, list[tuple[dict[str, Any], dict[str, Any]]]] = defaultdict(list)
    for case_id, row in expected.items():
        grouped[row["task_type"]].append((row, prediction_map[case_id]))
    certificate = score_certificate(grouped["CERTIFICATE"])
    transition = score_transition(grouped["TRANSITION"])
    queue = score_queue(grouped["QUEUE_TRACE"])
    pair = score_pair(grouped["PAIR_CONTRAST"])
    return {
        "schema_version": "cerebrum-execution-transfer-repair-evaluation.v1",
        "protocol_id": "CEREBRUM-DEV-009",
        "condition": condition,
        "seed": seed,
        "examples": len(expected_rows),
        "certificate": certificate,
        "transition": transition,
        "queue_trace": queue,
        "pair_contrast": pair,
        "advancement_gate": advancement_gate(certificate, transition, queue, pair),
        "deterministic_compiler": True,
        "hashes_derived_from_model_predicted_states": True,
        "public_scored": False,
        "binding_authority": False,
        "claim_boundary": "Fresh-lineage internal synthetic multi-generator repair validation only; no Transfer-007 case reuse and no public, protected, real-institution, autonomous-authority, or production claim.",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--predictions", type=Path, required=True)
    parser.add_argument("--expected", type=Path, default=ROOT / "prepared" / "fresh-validation-all.jsonl")
    parser.add_argument("--condition", required=True)
    parser.add_argument("--seed", type=int)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = score(read_jsonl(args.predictions), read_jsonl(args.expected), args.condition, args.seed)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())