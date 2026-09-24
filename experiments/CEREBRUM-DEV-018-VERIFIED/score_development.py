#!/usr/bin/env python3
"""Score model-only and verified-hybrid development behavior separately."""

from __future__ import annotations

import json

from dev018_common import CONFIG, ROOT, read_json, read_jsonl, sha256_path, write_json
from prepare_data import prepare
from scoring import score_rows


def main() -> int:
    prepare()
    config = read_json(CONFIG)
    model_freeze_path = ROOT / "results" / "development-model-prediction-freeze.json"
    verification_freeze_path = ROOT / "results" / "development-verification-freeze.json"
    if not model_freeze_path.is_file() or not verification_freeze_path.is_file():
        raise SystemExit("development scoring locked until model and verification freezes exist")
    model_freeze = read_json(model_freeze_path)
    verification_freeze = read_json(verification_freeze_path)
    if model_freeze.get("complete") is not True or verification_freeze.get("complete") is not True:
        raise SystemExit("development predictions are incomplete")
    expected_path = ROOT / "prepared" / "development-selection-64.jsonl"
    model_path = ROOT / "results" / "development-model-predictions.jsonl"
    verified_path = ROOT / "results" / "development-verified-predictions.jsonl"
    audit_path = ROOT / "results" / "development-verification-audit.jsonl"
    if model_freeze["predictions_sha256"] != sha256_path(model_path):
        raise SystemExit("model predictions changed after freeze")
    if verification_freeze["verified_predictions_sha256"] != sha256_path(verified_path):
        raise SystemExit("verified predictions changed after freeze")
    expected = read_jsonl(expected_path)
    model_metrics = score_rows(expected, read_jsonl(model_path), config, "dev018_model_only")
    hybrid_metrics = score_rows(expected, read_jsonl(verified_path), config, "dev018_verified_hybrid")
    audits = read_jsonl(audit_path)
    controls = {
        "development_count_64": len(expected) == 64,
        "model_prediction_count_64": len(read_jsonl(model_path)) == 64,
        "verified_prediction_count_64": len(read_jsonl(verified_path)) == 64,
        "audit_count_64": len(audits) == 64,
        "all_answer_key_access_flags_false": all(row["answer_key_accessed"] is False for row in audits),
        "every_case_has_verifier_action": all(row["action"] in {"ACCEPT_MODEL", "OVERRIDE_WITH_EXECUTOR"} for row in audits),
        "all_26_hybrid_checks_pass": hybrid_metrics["full_regression_gate"]["passed"] is True,
        "zero_hybrid_unsafe_authorizations": hybrid_metrics["certificate"]["unsafe_authorizations"] == 0,
        "zero_hybrid_generation_limit_hits": (
            hybrid_metrics["certificate"]["output_reliability"]["generation_limit_hits"]
            + hybrid_metrics["transition"]["output_reliability"]["generation_limit_hits"]
            + hybrid_metrics["queue_trace"]["output_reliability"]["generation_limit_hits"]
            + hybrid_metrics["pair_contrast"]["output_reliability"]["generation_limit_hits"]
        ) == 0,
        "model_and_hybrid_metrics_separate": True,
    }
    passed = all(controls.values())
    result = {
        "schema_version": "cerebrum-dev018-development-result.v1",
        "protocol_id": config["protocol_id"],
        "status": "VERIFIED_HYBRID_DEVELOPMENT_PASS" if passed else "VERIFIED_HYBRID_DEVELOPMENT_HOLD",
        "passed": passed,
        "controls": controls,
        "controls_passed": sum(controls.values()),
        "control_count": len(controls),
        "model_only_metrics": model_metrics,
        "verified_hybrid_metrics": hybrid_metrics,
        "accepted_model_outputs": verification_freeze["accepted_model_outputs"],
        "overridden_model_outputs": verification_freeze["overridden_model_outputs"],
        "model_acceptance_rate": verification_freeze["model_acceptance_rate"],
        "safety_overrides": verification_freeze["safety_overrides"],
        "model_prediction_freeze_sha256": sha256_path(model_freeze_path),
        "verification_freeze_sha256": sha256_path(verification_freeze_path),
        "confirmation_scored": False,
        "full_regression": False,
        "training_steps": 0,
        "binding_authority": False,
        "transfer_authorized": False,
        "claim_boundary": "Development-only synthetic integration evidence. Hybrid accuracy is attributable to the deterministic executor and verifier, not evidence that the frozen language model learned the policy.",
    }
    write_json(ROOT / "results" / "development-result.json", result)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())