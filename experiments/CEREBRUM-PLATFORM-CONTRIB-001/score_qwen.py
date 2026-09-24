#!/usr/bin/env python3
"""Single-use protected scorer for the registered Qwen contribution conditions."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent


def digest(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def load(path: Path):
    return [json.loads(line) for line in path.read_text().splitlines() if line]


def metrics(predictions, labels):
    targets = {row["case_id"]: row["target"] for row in labels}
    decision = risk = capacity = joint = unsafe = parse_errors = 0
    risk_error = 0.0
    for row in predictions:
        target = targets[row["case_id"]]
        predicted = row["prediction"]
        parse_errors += bool(predicted.get("parse_error"))
        decision_ok = predicted.get("decision") == target["decision"]
        risk_ok = predicted.get("risk_band") == target["risk_band"]
        capacity_ok = predicted.get("capacity_band") == target["capacity_band"]
        decision += decision_ok
        risk += risk_ok
        capacity += capacity_ok
        joint += decision_ok and risk_ok and capacity_ok
        unsafe += predicted.get("decision") == "ALLOW" and target["decision"] != "ALLOW"
        try:
            risk_error += abs(float(predicted.get("risk_score")) - float(target["risk_score"]))
        except (TypeError, ValueError):
            risk_error += 1.0
    count = len(labels)
    return {
        "decision_accuracy": decision / count,
        "risk_band_accuracy": risk / count,
        "capacity_band_accuracy": capacity / count,
        "joint_accuracy": joint / count,
        "risk_mae": risk_error / count,
        "unsafe_authorizations": unsafe,
        "parse_errors": parse_errors,
    }


def main() -> int:
    receipt = ROOT / "results" / "qwen_score_receipt.json"
    if receipt.exists():
        raise SystemExit("protected Qwen score transaction has already been consumed")
    freeze_path = ROOT / "results" / "qwen_prediction_freeze.json"
    if not freeze_path.is_file():
        raise SystemExit("predictions must be hash-frozen before scoring")
    freeze = json.loads(freeze_path.read_text())
    labels = load(ROOT / "protected" / "labels.jsonl")
    scored = {"control": [], "platform002": []}
    for record in freeze["predictions"]:
        path = ROOT / record["path"]
        if digest(path) != record["sha256"]:
            raise SystemExit("prediction hash mismatch")
        scored[record["condition"]].append({
            "seed": record["seed"], **metrics(load(path), labels)
        })
    control_joint = sum(row["joint_accuracy"] for row in scored["control"]) / 2
    control_decision = sum(row["decision_accuracy"] for row in scored["control"]) / 2
    control_risk = sum(row["risk_band_accuracy"] for row in scored["control"]) / 2
    gates = {
        "all_four_prediction_files_scored": sum(len(rows) for rows in scored.values()) == 4,
        "both_platform002_seeds_decision_gain_005": all(row["decision_accuracy"] >= control_decision + 0.05 for row in scored["platform002"]),
        "both_platform002_seeds_risk_gain_010": all(row["risk_band_accuracy"] >= control_risk + 0.10 for row in scored["platform002"]),
        "both_platform002_seeds_joint_gain_010": all(row["joint_accuracy"] >= control_joint + 0.10 for row in scored["platform002"]),
        "zero_platform002_unsafe_authorizations": all(row["unsafe_authorizations"] == 0 for row in scored["platform002"]),
        "zero_platform002_parse_errors": all(row["parse_errors"] == 0 for row in scored["platform002"]),
    }
    result = {
        "schema_version": "cerebrum-platform-contrib-qwen-result.v1",
        "experiment_id": "CEREBRUM-PLATFORM-CONTRIB-001",
        "status": "PLATFORM002_QWEN_DEVELOPMENT_SIGNAL_ESTABLISHED" if all(gates.values()) else "PLATFORM002_QWEN_DEVELOPMENT_SIGNAL_NOT_ESTABLISHED",
        "gates": gates, "conditions": scored,
        "binding_authority": False,
        "claim_boundary": "Development-only Qwen diagnostic on a target already opened for proxy scoring; not confirmatory Cerebrum evidence.",
    }
    (ROOT / "results" / "qwen_result.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    receipt.write_text(json.dumps({
        "experiment_id": result["experiment_id"],
        "prediction_freeze_sha256": digest(freeze_path),
        "protected_labels_sha256": digest(ROOT / "protected" / "labels.jsonl"),
        "result_status": result["status"],
    }, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if all(gates.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())