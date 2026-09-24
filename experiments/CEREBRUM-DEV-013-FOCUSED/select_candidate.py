#!/usr/bin/env python3
"""Apply the preregistered safety-first development checkpoint selector."""

from __future__ import annotations

import json
from typing import Any

from dev013_common import CONFIG, ROOT, candidate_specs, read_json, read_jsonl, sha256_path, sha256_tree, write_json
from prepare_data import prepare
from scoring import load_scorer


def eligibility(metrics: dict[str, Any], config: dict[str, Any]) -> dict[str, bool]:
    gate = config["selection_gate"]
    return {
        "raw_schema_validity_1": metrics["raw_schema_validity"] == gate["raw_schema_validity"],
        "certificate_validity_1": metrics["certificate_validity"] == gate["certificate_validity"],
        "decision_accuracy_floor": metrics["decision_accuracy"] >= gate["decision_accuracy_min"],
        "resolved_allow_accuracy_floor": metrics["resolved_allow_accuracy"] >= gate["resolved_allow_accuracy_min"],
        "unresolved_contested_exact": metrics["unresolved_contested_accuracy"] == gate["unresolved_contested_accuracy"],
        "zero_unsafe_authorizations": metrics["unsafe_authorizations"] <= gate["unsafe_authorizations_max"],
        "zero_generation_limit_hits": metrics["output_reliability"]["generation_limit_hits"] <= gate["generation_limit_hits_max"],
    }


def choose_candidate(rows: list[dict[str, Any]]) -> dict[str, Any] | None:
    eligible = [row for row in rows if row["eligible"]]
    if not eligible:
        return None
    return max(
        eligible,
        key=lambda row: (
            row["metrics"]["resolved_allow_accuracy"],
            row["metrics"]["paired_boundary_exact"],
            row["metrics"]["decision_accuracy"],
            -int(row["step"]),
        ),
    )


def main() -> int:
    prepare()
    config = read_json(CONFIG)
    freeze_path = ROOT / "results" / "development-prediction-freeze.json"
    if not freeze_path.is_file():
        raise SystemExit("development selection locked until all candidate predictions are frozen")
    freeze = read_json(freeze_path)
    if freeze.get("all_complete") is not True:
        raise SystemExit("development candidate predictions are incomplete")
    selection_path = ROOT / "results" / "selected-candidate.json"
    if selection_path.is_file():
        existing = read_json(selection_path)
        if existing.get("development_prediction_freeze_sha256") != sha256_path(freeze_path):
            raise SystemExit("existing selection is bound to a different development prediction freeze")
        print(json.dumps(existing, indent=2, sort_keys=True))
        return 0
    expected = read_jsonl(ROOT / "prepared" / "development-selection-32.jsonl")
    scorer = load_scorer()
    evaluator = scorer.load_evaluator()
    frozen_candidates = {item["candidate_id"]: item for item in freeze["candidates"]}
    rows = []
    for candidate in candidate_specs(config):
        path = ROOT / "results" / f"development-{candidate['candidate_id']}-predictions.jsonl"
        frozen = frozen_candidates.get(candidate["candidate_id"])
        if frozen is None:
            raise SystemExit(f"candidate missing from development freeze: {candidate['candidate_id']}")
        if sha256_path(path) != frozen["predictions_sha256"]:
            raise SystemExit(f"candidate predictions changed after freeze: {candidate['candidate_id']}")
        if sha256_tree(candidate["adapter"]) != frozen["adapter_tree_sha256"]:
            raise SystemExit(f"candidate adapter changed after prediction: {candidate['candidate_id']}")
        metrics = scorer.score_seed(expected, read_jsonl(path), evaluator, config)
        checks = eligibility(metrics, config)
        rows.append({
            "candidate_id": candidate["candidate_id"],
            "step": candidate["step"],
            "adapter_tree_sha256": frozen["adapter_tree_sha256"],
            "predictions_sha256": sha256_path(path),
            "eligible": all(checks.values()),
            "eligibility_checks": checks,
            "metrics": metrics,
        })
    selected = choose_candidate(rows)
    result = {
        "schema_version": "cerebrum-dev013-development-selection.v1",
        "protocol_id": config["protocol_id"],
        "development_input_sha256": sha256_path(ROOT / "prepared" / "development-selection-32.jsonl"),
        "development_prediction_freeze_sha256": sha256_path(freeze_path),
        "selection_rule": config["selection_ranking"],
        "candidate_results": rows,
        "selected_candidate_id": selected["candidate_id"] if selected else None,
        "selected_step": selected["step"] if selected else None,
        "selected_adapter_tree_sha256": selected["adapter_tree_sha256"] if selected else None,
        "status": "SAFE_DEVELOPMENT_CANDIDATE_SELECTED" if selected else "NO_SAFE_DEVELOPMENT_CANDIDATE",
        "confirmation_scored": False,
        "full_regression": False,
        "transfer_authorized": False,
        "binding_authority": False,
        "claim_boundary": "Adaptive development checkpoint selection only; no confirmation, regression, or transfer claim.",
    }
    write_json(selection_path, result)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())