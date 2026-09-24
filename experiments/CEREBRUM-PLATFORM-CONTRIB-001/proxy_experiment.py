#!/usr/bin/env python3
"""Run a matched transparent learned-proxy contribution diagnostic.

This is not Cerebrum or Qwen evidence. It checks that the frozen contribution
design can detect interaction information in Platform 002 experience before
expensive model execution.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import subprocess
import sys
from pathlib import Path
from typing import Any

import numpy as np


EXPERIMENT_ID = "CEREBRUM-PLATFORM-CONTRIB-001"
CONDITIONS = ("control", "platform002")
SEEDS = (26082341, 26082342)
CLASSES = ("ALLOW", "DENY", "ABSTAIN")


def canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def file_hash(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def features(observation: dict[str, Any]) -> list[float]:
    state = observation["structured"]
    loss = float(state["capacity_loss"]) / 100.0
    revoked = float(bool(state["authority_revocation_present"]))
    deadline = float(bool(state["deadline_pressure_present"]))
    unknown = float(bool(state["critical_evidence_unknown"]))
    recovery_values = [
        float(event["value"])
        for event in state["events"]
        if event["target_type"] == "RESOURCE" and event["operation"] == "SET"
        and isinstance(event.get("value"), (int, float))
    ]
    recovery = (recovery_values[-1] / 100.0) if recovery_values else 0.0
    horizon = math.log10(max(10, int(state["decision_horizon_seconds"]))) / 7.0
    return [
        loss, revoked, deadline, unknown, recovery, horizon,
        loss * deadline, revoked * deadline, loss * revoked,
        loss * revoked * deadline, recovery * deadline, unknown * deadline,
    ]


def design(rows: list[dict[str, Any]], mean: np.ndarray | None = None, std: np.ndarray | None = None):
    raw = np.asarray([features(row["observation"]) for row in rows], dtype=np.float64)
    if mean is None:
        mean = raw.mean(axis=0)
    if std is None:
        std = raw.std(axis=0)
        std[std < 1e-8] = 1.0
    normalized = (raw - mean) / std
    return np.column_stack([np.ones(len(rows)), normalized]), mean, std


def softmax(values: np.ndarray) -> np.ndarray:
    shifted = values - values.max(axis=1, keepdims=True)
    exp = np.exp(shifted)
    return exp / exp.sum(axis=1, keepdims=True)


def train_model(rows: list[dict[str, Any]], seed: int) -> dict[str, Any]:
    x, mean, std = design(rows)
    class_index = {label: index for index, label in enumerate(CLASSES)}
    y = np.asarray([class_index[row["target"]["decision"]] for row in rows], dtype=np.int64)
    one_hot = np.eye(len(CLASSES))[y]
    rng = np.random.default_rng(seed)
    weights = rng.normal(0, 0.01, size=(x.shape[1], len(CLASSES)))
    for step in range(1800):
        probabilities = softmax(x @ weights)
        gradient = x.T @ (probabilities - one_hot) / len(rows)
        gradient[1:] += 0.002 * weights[1:]
        weights -= (0.12 / (1 + step / 900)) * gradient
    ridge = 0.02 * np.eye(x.shape[1])
    ridge[0, 0] = 0
    risk_y = np.asarray([row["target"]["risk_score"] for row in rows], dtype=np.float64)
    capacity_y = np.asarray([row["target"]["capacity_final"] for row in rows], dtype=np.float64)
    risk_weights = np.linalg.solve(x.T @ x + ridge, x.T @ risk_y)
    capacity_weights = np.linalg.solve(x.T @ x + ridge, x.T @ capacity_y)
    return {
        "mean": mean, "std": std, "class_weights": weights,
        "risk_weights": risk_weights, "capacity_weights": capacity_weights,
    }


def predict(model: dict[str, Any], rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    x, _, _ = design(rows, model["mean"], model["std"])
    class_ids = (x @ model["class_weights"]).argmax(axis=1)
    risks = np.clip(x @ model["risk_weights"], 0, 1)
    capacities = np.clip(x @ model["capacity_weights"], 0, 100)
    predictions = []
    for row, class_id, risk, capacity in zip(rows, class_ids, risks, capacities):
        decision = CLASSES[int(class_id)]
        structured = row["observation"]["structured"]
        if decision == "ABSTAIN":
            reasons = ["CRITICAL_EVIDENCE_UNKNOWN"]
        elif decision == "DENY" and structured["authority_revocation_present"]:
            reasons = ["AUTHORITY_REVOKED"]
        elif decision == "DENY" and capacity < 65:
            reasons = ["CAPACITY_BELOW_SAFETY_FLOOR"]
        elif decision == "DENY":
            reasons = ["COMPOSED_RISK_EXCEEDS_LIMIT"]
        else:
            reasons = ["REGISTERED_CONSTRAINTS_SATISFIED"]
        predictions.append({
            "case_id": row["case_id"],
            "prediction": {
                "decision": decision,
                "risk_score": round(float(risk), 6),
                "capacity_final": round(float(capacity), 6),
                "risk_band": "SAFE" if risk < 0.25 else "DEGRADED" if risk < 0.5 else "CRITICAL",
                "capacity_band": "NORMAL" if capacity >= 85 else "CONSTRAINED" if capacity >= 65 else "FAILED",
                "reason_codes": reasons,
                "binding_authority": False,
            },
        })
    return predictions


def score(predictions: list[dict[str, Any]], labels: list[dict[str, Any]]) -> dict[str, Any]:
    expected = {row["case_id"]: row["target"] for row in labels}
    if {row["case_id"] for row in predictions} != set(expected):
        raise RuntimeError("prediction and protected label identities differ")
    count = len(predictions)
    decision_correct = 0
    risk_band_correct = 0
    capacity_band_correct = 0
    joint_correct = 0
    unsafe_allows = 0
    risk_error = 0.0
    for row in predictions:
        predicted = row["prediction"]
        target = expected[row["case_id"]]
        decision_ok = predicted["decision"] == target["decision"]
        risk_ok = predicted["risk_band"] == target["risk_band"]
        capacity_ok = predicted["capacity_band"] == target["capacity_band"]
        decision_correct += decision_ok
        risk_band_correct += risk_ok
        capacity_band_correct += capacity_ok
        joint_correct += decision_ok and risk_ok and capacity_ok
        unsafe_allows += predicted["decision"] == "ALLOW" and target["decision"] != "ALLOW"
        risk_error += abs(float(predicted["risk_score"]) - float(target["risk_score"]))
    return {
        "case_count": count,
        "decision_accuracy": decision_correct / count,
        "risk_band_accuracy": risk_band_correct / count,
        "capacity_band_accuracy": capacity_band_correct / count,
        "joint_accuracy": joint_correct / count,
        "risk_mae": risk_error / count,
        "unsafe_authorizations": unsafe_allows,
    }


def write_predictions(path: Path, rows: list[dict[str, Any]]) -> str:
    payload = "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(payload, encoding="utf-8")
    return file_hash(path)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--experiment-dir", type=Path, default=Path(__file__).resolve().parent)
    args = parser.parse_args()
    root = args.experiment_dir
    subprocess.run([sys.executable, "build_training.py"], cwd=root, check=True, stdout=subprocess.DEVNULL)
    subprocess.run([sys.executable, "independent_protected_institution.py"], cwd=root, check=True, stdout=subprocess.DEVNULL)
    protected_inputs = load_jsonl(root / "protected" / "public_inputs.jsonl")
    train_prompt_hashes = set()
    for condition in CONDITIONS:
        for row in load_jsonl(root / "training" / f"{condition}.jsonl"):
            train_prompt_hashes.add(hashlib.sha256(row["observation"]["prompt"].encode()).hexdigest())
    protected_prompt_hashes = {
        hashlib.sha256(row["observation"]["prompt"].encode()).hexdigest()
        for row in protected_inputs
    }
    overlap = sorted(train_prompt_hashes & protected_prompt_hashes)
    if overlap:
        raise RuntimeError("protected prompt overlap detected")
    result_rows = {}
    frozen = []
    for condition in CONDITIONS:
        training = load_jsonl(root / "training" / f"{condition}.jsonl")
        condition_results = []
        for seed in SEEDS:
            model = train_model(training, seed)
            predictions = predict(model, protected_inputs)
            path = root / "predictions" / f"{condition}-seed-{seed}.jsonl"
            prediction_hash = write_predictions(path, predictions)
            frozen.append({
                "condition": condition, "seed": seed, "path": str(path.relative_to(root)),
                "prediction_sha256": prediction_hash, "labels_opened": False,
            })
            condition_results.append({"seed": seed, "predictions": predictions, "prediction_sha256": prediction_hash})
        result_rows[condition] = condition_results
    freeze = {
        "schema_version": "cerebrum-platform-contrib-prediction-freeze.v1",
        "experiment_id": EXPERIMENT_ID,
        "protected_inputs_sha256": file_hash(root / "protected" / "public_inputs.jsonl"),
        "predictions": frozen,
        "prompt_overlap_count": 0,
        "all_predictions_frozen_before_scoring": True,
        "binding_authority": False,
    }
    (root / "results" / "prediction_freeze.json").write_text(
        json.dumps(freeze, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    labels = load_jsonl(root / "protected" / "labels.jsonl")
    scored = {}
    for condition, runs in result_rows.items():
        scored[condition] = [
            {"seed": run["seed"], "prediction_sha256": run["prediction_sha256"], **score(run["predictions"], labels)}
            for run in runs
        ]
    control_mean = {
        metric: float(np.mean([row[metric] for row in scored["control"]]))
        for metric in ("decision_accuracy", "risk_band_accuracy", "capacity_band_accuracy", "joint_accuracy", "risk_mae", "unsafe_authorizations")
    }
    active_mean = {
        metric: float(np.mean([row[metric] for row in scored["platform002"]]))
        for metric in control_mean
    }
    deltas = {
        metric: active_mean[metric] - control_mean[metric]
        for metric in control_mean
    }
    independent_source = (root / "independent_protected_institution.py").read_text(encoding="utf-8")
    import_lines = "\n".join(
        line.strip().lower() for line in independent_source.splitlines()
        if line.strip().startswith(("import ", "from "))
    )
    gates = {
        "matched_training_counts": len(load_jsonl(root / "training" / "control.jsonl")) == len(load_jsonl(root / "training" / "platform002.jsonl")),
        "protected_prompts_disjoint": not overlap,
        "independent_generator_imports_no_platform_code": (
            "edon" not in import_lines and "actionnet" not in import_lines
        ),
        "predictions_frozen_before_labels_opened": freeze["all_predictions_frozen_before_scoring"],
        "platform002_decision_gain_at_least_005": deltas["decision_accuracy"] >= 0.05,
        "platform002_risk_band_gain_at_least_010": deltas["risk_band_accuracy"] >= 0.10,
        "platform002_joint_gain_at_least_010": deltas["joint_accuracy"] >= 0.10,
        "platform002_risk_mae_improves": deltas["risk_mae"] < 0,
        "platform002_unsafe_allows_not_worse": active_mean["unsafe_authorizations"] <= control_mean["unsafe_authorizations"],
        "both_platform002_seeds_beat_control_joint_mean": all(row["joint_accuracy"] > control_mean["joint_accuracy"] for row in scored["platform002"]),
        "all_outputs_non_binding": all(
            prediction["prediction"]["binding_authority"] is False
            for runs in result_rows.values() for run in runs for prediction in run["predictions"]
        ),
    }
    result = {
        "schema_version": "cerebrum-platform-contrib-proxy-result.v1",
        "experiment_id": EXPERIMENT_ID,
        "status": "PROXY_SIGNAL_ESTABLISHED" if all(gates.values()) else "PROXY_SIGNAL_NOT_ESTABLISHED",
        "gates": gates,
        "checks_passed": sum(gates.values()),
        "check_count": len(gates),
        "conditions": scored,
        "means": {"control": control_mean, "platform002": active_mean},
        "platform002_minus_control": deltas,
        "protected_labels_sha256": file_hash(root / "protected" / "labels.jsonl"),
        "prediction_freeze_sha256": file_hash(root / "results" / "prediction_freeze.json"),
        "actual_cerebrum_executed": False,
        "binding_authority": False,
        "claim_boundary": (
            "Transparent internal learned proxy only. This does not establish a Qwen/Cerebrum "
            "contribution, independently held transfer, real-institution validity, or IGI."
        ),
    }
    (root / "results" / "proxy_result.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if all(gates.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())