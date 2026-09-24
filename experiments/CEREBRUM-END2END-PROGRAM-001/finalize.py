#!/usr/bin/env python3
"""Issue the bounded final Program-001 result."""

from __future__ import annotations

import json

from program_common import CONFIG, ROOT, read_json, sha256_path, write_json


def main() -> int:
    config = read_json(CONFIG)
    selection_path = ROOT / "results" / "selected-candidate.json"
    selection = read_json(selection_path)
    if not selection.get("selected_candidate_id"):
        result = {
            "schema_version": "cerebrum-program-001-result.v1",
            "protocol_id": config["protocol_id"],
            "status": "NO_PROGRAM_CANDIDATE_PASSES_DEVELOPMENT_GATE",
            "passed": False,
            "confirmation_accessed": False,
            "selection_sha256": sha256_path(selection_path),
            "training_steps": config["max_steps"],
            "transfer_authorized": False,
            "binding_authority": False,
            "claim_boundary": "Development hold; no confirmation or capability claim.",
        }
    else:
        confirmation_path = ROOT / "results" / "confirmation-prediction-freeze.json"
        score_path = ROOT / "results" / "confirmation-score.json"
        learning_effect_path = ROOT / "results" / "confirmation-learning-effect.json"
        confirmation = read_json(confirmation_path)
        score = read_json(score_path)
        learning_effect = read_json(learning_effect_path)
        passed = (
            confirmation["complete"]
            and confirmation["gate_passed"]
            and score["gate_passed"]
            and learning_effect["improvement_gate_passed"]
        )
        result = {
            "schema_version": "cerebrum-program-001-result.v1",
            "protocol_id": config["protocol_id"],
            "status": "NATIVE_TEMPORAL_PROGRAM_SIGNAL" if passed else "PROGRAM_CONFIRMATION_HOLD",
            "passed": passed,
            "selected_candidate_id": selection["selected_candidate_id"],
            "selected_step": selection["selected_step"],
            "confirmation_accessed": True,
            "selection_sha256": sha256_path(selection_path),
            "confirmation_freeze_sha256": sha256_path(confirmation_path),
            "confirmation_score_sha256": sha256_path(score_path),
            "learning_effect_sha256": sha256_path(learning_effect_path),
            "analysis": score,
            "learning_effect": learning_effect,
            "verified_envelope_unsafe_authorizations": score["verified_envelope_unsafe_authorizations"],
            "verified_envelope_coverage": score["verified_envelope_coverage"],
            "training_steps": config["max_steps"],
            "transfer_authorized": False,
            "binding_authority": False,
            "claim_boundary": (
                "Fresh synthetic in-distribution native temporal-program training effect for one registered seed. "
                "A pass supports paired improvement over the untrained base plus absolute executable-program gates; "
                "it does not establish seed-robust causality, external transfer, "
                "production authority, autonomous deployment, or IGI."
            ),
        }
    write_json(ROOT / "results" / "program-001-result.json", result)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())