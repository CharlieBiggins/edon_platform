#!/usr/bin/env python3
"""Open the single-use confirmation split only after development selection."""

from __future__ import annotations

import json
import subprocess
import sys

from program_common import CONFIG, ROOT, candidate_specs, read_json, sha256_path, sha256_tree, write_json
from scoring import paired_improvement


def main() -> int:
    config = read_json(CONFIG)
    selection_path = ROOT / "results" / "selected-candidate.json"
    selection = read_json(selection_path)
    selected_id = selection.get("selected_candidate_id")
    if not selected_id:
        print(json.dumps({
            "status": "CONFIRMATION_REMAINS_SEALED",
            "reason": "No checkpoint passed every development gate.",
        }, indent=2, sort_keys=True))
        return 0
    candidates = {candidate["candidate_id"]: candidate for candidate in candidate_specs(config)}
    selected = candidates[selected_id]
    input_path = ROOT / "prepared" / "untouched-confirmation-256.jsonl"
    base = config["base_control"]
    base_predictions = ROOT / "results" / "confirmation-base-control-predictions.jsonl"
    subprocess.run([
        sys.executable, str(ROOT / "predict.py"),
        "--config", str(CONFIG),
        "--input", str(input_path),
        "--output", str(base_predictions),
    ], cwd=ROOT, check=True)
    base_score_path = ROOT / "results" / "confirmation-base-control-score.json"
    subprocess.run([
        sys.executable, str(ROOT / "score.py"),
        "--input", str(input_path),
        "--predictions", str(base_predictions),
        "--output", str(base_score_path),
        "--candidate-id", base["candidate_id"],
        "--candidate-step", "0",
        "--gate", "confirmation",
    ], cwd=ROOT, check=True)
    predictions = ROOT / "results" / "confirmation-predictions.jsonl"
    subprocess.run([
        sys.executable, str(ROOT / "predict.py"),
        "--config", str(CONFIG),
        "--adapter", str(selected["adapter"]),
        "--input", str(input_path),
        "--output", str(predictions),
    ], cwd=ROOT, check=True)
    score_path = ROOT / "results" / "confirmation-score.json"
    subprocess.run([
        sys.executable, str(ROOT / "score.py"),
        "--input", str(input_path),
        "--predictions", str(predictions),
        "--output", str(score_path),
        "--candidate-id", selected_id,
        "--candidate-step", str(selected["step"]),
        "--gate", "confirmation",
    ], cwd=ROOT, check=True)
    score = read_json(score_path)
    base_score = read_json(base_score_path)
    learning_effect = paired_improvement(
        base_score["evaluations"],
        score["evaluations"],
        config["confirmation_improvement_gate"],
    )
    learning_effect_path = ROOT / "results" / "confirmation-learning-effect.json"
    write_json(learning_effect_path, {
        "schema_version": "cerebrum-program-001-learning-effect.v1",
        "protocol_id": config["protocol_id"],
        "split": "confirmation",
        "base_candidate_id": base["candidate_id"],
        "trained_candidate_id": selected_id,
        **learning_effect,
        "base_score_sha256": sha256_path(base_score_path),
        "trained_score_sha256": sha256_path(score_path),
        "transfer_authorized": False,
        "binding_authority": False,
    })
    freeze = {
        "schema_version": "cerebrum-program-001-confirmation-freeze.v1",
        "protocol_id": config["protocol_id"],
        "selected_candidate_id": selected_id,
        "selected_step": selected["step"],
        "adapter_tree_sha256": sha256_tree(selected["adapter"]),
        "selection_sha256": sha256_path(selection_path),
        "input_sha256": sha256_path(input_path),
        "base_control_predictions_sha256": sha256_path(base_predictions),
        "base_control_score_sha256": sha256_path(base_score_path),
        "predictions_sha256": sha256_path(predictions),
        "score_sha256": sha256_path(score_path),
        "learning_effect_sha256": sha256_path(learning_effect_path),
        "count_per_arm": score["examples"],
        "total_predictions": score["examples"] + base_score["examples"],
        "complete": (
            score["examples"] == config["confirmation_records"]
            and base_score["examples"] == config["confirmation_records"]
            and learning_effect["paired_cases"] == config["confirmation_records"]
        ),
        "absolute_gate_passed": score["gate_passed"],
        "learning_effect_passed": learning_effect["improvement_gate_passed"],
        "gate_passed": score["gate_passed"] and learning_effect["improvement_gate_passed"],
        "confirmation_accessed": True,
        "transfer_authorized": False,
        "binding_authority": False,
    }
    write_json(ROOT / "results" / "confirmation-prediction-freeze.json", freeze)
    print(json.dumps(freeze, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())