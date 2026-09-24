#!/usr/bin/env python3
"""Select at most one checkpoint using only the development split."""

from __future__ import annotations

import json

from program_common import CONFIG, ROOT, candidate_specs, read_json, sha256_path, write_json
from scoring import paired_improvement


def main() -> int:
    config = read_json(CONFIG)
    freeze_path = ROOT / "results" / "development-prediction-freeze.json"
    freeze = read_json(freeze_path)
    base_score_path = ROOT / "results" / "development-base-control-score.json"
    base_score = read_json(base_score_path)
    candidates = []
    for candidate in candidate_specs(config):
        score_path = ROOT / "results" / f"development-{candidate['candidate_id']}-score.json"
        score = read_json(score_path)
        learning_effect = paired_improvement(
            base_score["evaluations"],
            score["evaluations"],
            config["development_improvement_gate"],
        )
        learning_effect.update({
            "schema_version": "cerebrum-program-001-improvement-comparison.v1",
            "protocol_id": config["protocol_id"],
            "split": "development",
            "base_candidate_id": config["base_control"]["candidate_id"],
            "trained_candidate_id": candidate["candidate_id"],
            "base_score_sha256": sha256_path(base_score_path),
            "trained_score_sha256": sha256_path(score_path),
        })
        learning_effect_path = ROOT / "results" / f"development-{candidate['candidate_id']}-improvement.json"
        write_json(learning_effect_path, learning_effect)
        candidates.append({
            **candidate,
            "score": score,
            "score_path": score_path,
            "learning_effect": learning_effect,
            "learning_effect_path": learning_effect_path,
        })
    passing = [
        candidate for candidate in candidates
        if candidate["score"]["gate_passed"] and candidate["learning_effect"]["improvement_gate_passed"]
    ]
    selected = None
    if passing:
        selected = sorted(passing, key=lambda candidate: (
            candidate["score"]["unsafe_authorizations"],
            -candidate["learning_effect"]["metrics"]["program_exact"]["delta"],
            -candidate["score"]["program_exact_rate"],
            -candidate["score"]["executed_state_exact_rate"],
            -candidate["score"]["decision_accuracy"],
            candidate["step"],
        ))[0]
    result = {
        "schema_version": "cerebrum-program-001-selection.v1",
        "protocol_id": config["protocol_id"],
        "status": "PROGRAM_CANDIDATE_SELECTED" if selected else "NO_PROGRAM_CANDIDATE_PASSES_DEVELOPMENT_GATE",
        "selected_candidate_id": selected["candidate_id"] if selected else None,
        "selected_step": selected["step"] if selected else None,
        "development_freeze_sha256": sha256_path(freeze_path),
        "base_control": {
            "candidate_id": base_score["candidate_id"],
            "score_sha256": sha256_path(base_score_path),
            "program_exact_rate": base_score["program_exact_rate"],
            "decision_accuracy": base_score["decision_accuracy"],
            "accepted_by_verifier_rate": base_score["accepted_by_verifier_rate"],
            "unsafe_authorizations": base_score["unsafe_authorizations"],
        },
        "candidate_scores": {
            candidate["candidate_id"]: {
                "score_sha256": sha256_path(candidate["score_path"]),
                "absolute_gate_passed": candidate["score"]["gate_passed"],
                "improvement_sha256": sha256_path(candidate["learning_effect_path"]),
                "learning_effect_passed": candidate["learning_effect"]["improvement_gate_passed"],
                "selection_gate_passed": (
                    candidate["score"]["gate_passed"]
                    and candidate["learning_effect"]["improvement_gate_passed"]
                ),
                "checks_passed": candidate["score"]["checks_passed"],
                "check_count": candidate["score"]["check_count"],
                "learning_effect": candidate["learning_effect"],
                "program_exact_rate": candidate["score"]["program_exact_rate"],
                "decision_accuracy": candidate["score"]["decision_accuracy"],
                "unsafe_authorizations": candidate["score"]["unsafe_authorizations"],
            }
            for candidate in candidates
        },
        "confirmation_accessed": False,
        "qualifying_candidate_count": len(passing),
        "selection_unique": selected is not None,
        "transfer_authorized": False,
        "binding_authority": False,
    }
    write_json(ROOT / "results" / "selected-candidate.json", result)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())