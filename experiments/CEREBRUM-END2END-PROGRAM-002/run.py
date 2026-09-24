"""Explicit stages; confirmation cannot run without a bound qualifying selection."""
from __future__ import annotations

import argparse
import fcntl
import json
import subprocess
import sys

from common import (ROOT, PROTOCOL, config, verify_freeze, read_json, read_rows,
                    file_hash, write_json, write_rows)
from evaluation import score, family_comparison


def score_split(split):
    from gpu import trained_manifest
    rows = read_rows(ROOT / f"prepared/{split}.jsonl")
    scores = {}
    for arm in config()["arms"]:
        trained = trained_manifest(arm)
        path = ROOT / f"results/{split}-{arm}-predictions.jsonl"
        binding = read_json(path.with_suffix(".manifest.json"))
        expected = {"arm": arm, "split": split,
                    "registration_sha256": file_hash(ROOT / "registration.json"),
                    "input_sha256": file_hash(ROOT / f"prepared/{split}.jsonl"),
                    "adapter_sha256": trained["adapter_sha256"],
                    "predictions_sha256": file_hash(path), "count": len(rows)}
        if binding != expected:
            raise ValueError("prediction manifest binding mismatch")
        scores[arm] = score(rows, read_rows(path), arm, split)
        scores[arm]["prediction_binding"] = binding
        write_json(ROOT / f"results/{split}-{arm}-score.json", scores[arm])
    return scores


def selection_payload(scores):
    comparison = family_comparison(scores["uniform"], scores["structural"])
    return {"protocol_id": PROTOCOL,
            "registration_sha256": file_hash(ROOT / "registration.json"),
            "status": "READY_FOR_CONFIRMATION" if comparison["passed"] else "DEVELOPMENT_HOLD",
            "selected_arm": "structural" if comparison["passed"] else None,
            "comparison": comparison,
            "scores": {arm: file_hash(ROOT / f"results/development-{arm}-score.json") for arm in config()["arms"]},
            "adapters": {arm: scores[arm]["prediction_binding"]["adapter_sha256"] for arm in config()["arms"]},
            "confirmation_accessed": False, "transfer_authorized": False, "binding_authority": False}


def require_selection():
    verify_freeze()
    selection = read_json(ROOT / "results/selection.json")
    # Recompute from bound raw development predictions; never trust a hand-edited pass flag.
    if selection != selection_payload(score_split("development")):
        raise ValueError("selection does not match frozen development evidence")
    if selection["status"] != "READY_FOR_CONFIRMATION":
        raise ValueError("development did not qualify; confirmation remains unmaterialized")
    return selection


def require_confirmation_access():
    require_selection()
    access = read_json(ROOT / "results/confirmation-access.json")
    expected = {"protocol_id": PROTOCOL, "selection_sha256": file_hash(ROOT / "results/selection.json"),
                "registration_sha256": file_hash(ROOT / "registration.json"),
                "single_use": True, "transfer_authorized": False, "binding_authority": False}
    if access != expected:
        raise ValueError("confirmation access binding mismatch")
    data_manifest = read_json(ROOT / "prepared/confirmation-manifest.json")
    if data_manifest["input_sha256"] != file_hash(ROOT / "prepared/confirmation.jsonl"):
        raise ValueError("confirmation data changed")


def worker(*args):
    subprocess.run([sys.executable, "-u", str(ROOT / "gpu.py"), *args], check=True, cwd=ROOT)


def development():
    verify_freeze()
    if (ROOT / "results/confirmation-access.json").exists():
        raise ValueError("development closed after confirmation access")
    # Both training arms finish before either development prediction is examined.
    for arm in config()["arms"]:
        worker("train", arm)
    for arm in config()["arms"]:
        worker("predict", arm, "--split", "development")
    result = selection_payload(score_split("development"))
    write_json(ROOT / "results/selection.json", result)
    print(json.dumps(result, indent=2))


def confirmation():
    require_selection()
    access = {"protocol_id": PROTOCOL, "selection_sha256": file_hash(ROOT / "results/selection.json"),
              "registration_sha256": file_hash(ROOT / "registration.json"),
              "single_use": True, "transfer_authorized": False, "binding_authority": False}
    # Record access before generation. A failed/interrupted run consumes access but may resume
    # the identical selected adapters, inputs and per-case output prefix, never retune.
    write_json(ROOT / "results/confirmation-access.json", access)
    from prepare import generate_split, validate_splits
    rows, audit = generate_split("confirmation", config())
    validate_splits({"train": read_rows(ROOT / "prepared/train.jsonl"),
                     "development": read_rows(ROOT / "prepared/development.jsonl"), "confirmation": rows})
    write_rows(ROOT / "prepared/confirmation.jsonl", rows)
    write_json(ROOT / "prepared/confirmation-manifest.json", {
        "input_sha256": file_hash(ROOT / "prepared/confirmation.jsonl"),
        "count": len(rows), "generator_audit": audit, "access": access})
    require_confirmation_access()
    for arm in config()["arms"]:
        worker("predict", arm, "--split", "confirmation")
    scores = score_split("confirmation")
    comparison = family_comparison(scores["uniform"], scores["structural"])
    result = {"protocol_id": PROTOCOL, "passed": comparison["passed"],
              "status": "CONFIRMED_SYNTHETIC_STRUCTURAL_LOSS_SIGNAL" if comparison["passed"] else "CONFIRMATION_HOLD",
              "comparison": comparison, "confirmation_accessed": True,
              "selection_sha256": file_hash(ROOT / "results/selection.json"),
              "score_sha256": {arm: file_hash(ROOT / f"results/confirmation-{arm}-score.json") for arm in config()["arms"]},
              "transfer_authorized": False, "binding_authority": False,
              "claim_boundary": "One-seed synthetic controlled-training evidence only; no general intelligence, real-world transfer, or production safety claim."}
    write_json(ROOT / "results/final.json", result)
    print(json.dumps(result, indent=2))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("stage", choices=["prepare", "preflight", "development", "confirmation"])
    args = parser.parse_args()
    with (ROOT / ".run.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        if args.stage == "prepare":
            from prepare import prepare
            print(json.dumps(prepare(), indent=2))
        elif args.stage == "preflight":
            verify_freeze()
            print("CPU_PREFLIGHT_PASSED; GPU runtime and token-length checks still required")
        elif args.stage == "development":
            development()
        else:
            confirmation()


if __name__ == "__main__":
    main()