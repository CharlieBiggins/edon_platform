"""Explicit paid inference on label-free protected Transfer-001 inputs."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path, PureWindowsPath
import sys
import time

ROOT = Path(__file__).resolve().parent
MATCHED001 = ROOT.parent / "CEREBRUM-ACTIONNET-MATCHED-001"
CANDIDATES = {"ordinary-a": ("A", "ordinary"), "actionnet-a": ("A", "actionnet"),
              "ordinary-b": ("B", "ordinary"), "actionnet-b": ("B", "actionnet")}


def relative(value):
    path = Path(value)
    if path.is_absolute() or PureWindowsPath(str(path)).drive: raise argparse.ArgumentTypeError("Use relative paths")
    return path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("run_dir", "candidate_run", "base_snapshot", "output_dir"):
        parser.add_argument("--" + name.replace("_", "-"), dest=name, type=relative, required=True)
    parser.add_argument("--candidate", choices=CANDIDATES, required=True)
    parser.add_argument("--maximum-gpu-hours", type=float, required=True)
    parser.add_argument("--authorize-paid", action="store_true")
    args = parser.parse_args()
    if not args.authorize_paid or args.maximum_gpu_hours <= 0: raise ValueError("Paid approval and positive cap required")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    sys.path.insert(0, str(MATCHED001)); import foundation, gpu_worker
    label, arm = CANDIDATES[args.candidate]
    registry = foundation.read(args.run_dir / "candidate-registry.json")[args.candidate]
    foundation.require(foundation.file_hash(args.candidate_run / "registration.json")
        == registry["training_registration_sha256"], "Candidate registration differs")
    study = foundation.read(args.candidate_run / "study.json"); config = foundation.read(MATCHED001 / "config.json")
    foundation.require(study["training_seed_label"] == label, "Candidate seed differs")
    trained = gpu_worker.trained_manifest(args.candidate_run, arm, config)
    foundation.require(foundation.file_hash(args.candidate_run / "artifacts" / arm / "training.json")
        == registry["training_manifest_sha256"] and trained["adapter_sha256"] == registry["adapter_sha256"],
        "Candidate artifact differs")
    inputs = foundation.rows(args.run_dir / "inputs.jsonl", "case_id")
    output = args.output_dir / (args.candidate + "-predictions.jsonl")
    manifest_path = output.with_suffix(".manifest.json")
    foundation.require(not manifest_path.exists(), "Candidate prediction is already complete")
    existing = foundation.rows(output, "case_id") if output.exists() else []
    foundation.require([row["case_id"] for row in existing] == [row["case_id"] for row in inputs[:len(existing)]],
                       "Prediction prefix differs")
    hashes = foundation.snapshot_hashes(args.base_snapshot)
    foundation.require(hashes["weights_tree_sha256"] == study["base_snapshot"]["weights_tree_sha256"], "Base differs")
    torch, _ = gpu_worker.runtime_environment(config); from peft import PeftModel
    base, tokenizer, _ = gpu_worker.load_base(torch, args.base_snapshot)
    model = PeftModel.from_pretrained(base, str(args.candidate_run / "artifacts" / arm / "adapter")); model.eval()
    started = time.monotonic(); cap = args.maximum_gpu_hours * 3600
    with output.open("ab") as stream:
        for index, item in enumerate(inputs[len(existing):], start=len(existing) + 1):
            foundation.require(time.monotonic() - started <= cap, "Inference cap reached")
            encoded = tokenizer(item["prompt"], return_tensors="pt", add_special_tokens=False)
            length = int(encoded["input_ids"].shape[-1]); one = time.monotonic()
            with torch.no_grad():
                generated = model.generate(**{key: value.to(model.device) for key, value in encoded.items()},
                    max_new_tokens=config["max_new_tokens"], do_sample=False,
                    pad_token_id=tokenizer.pad_token_id, eos_token_id=tokenizer.eos_token_id)
            tokens = generated[0, length:]; ended = bool(len(tokens) and int(tokens[-1]) == tokenizer.eos_token_id)
            row = {"case_id": item["case_id"], "raw_output": tokenizer.decode(tokens, skip_special_tokens=True).strip(),
                "ended_with_eos": ended, "hit_generation_limit": len(tokens) >= config["max_new_tokens"] and not ended,
                "prompt_token_count": length, "generated_token_count": len(tokens),
                "generation_seconds": time.monotonic() - one}
            stream.write((json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n").encode()); stream.flush(); os.fsync(stream.fileno())
            print(f"{args.candidate}: {index}/48", flush=True)
    manifest = {"protocol_id": "CEREBRUM-ACTIONNET-TRANSFER-001", "candidate": args.candidate,
        "count": 48, "predictions_sha256": foundation.file_hash(output), "adapter_sha256": trained["adapter_sha256"],
        "gpu_seconds": time.monotonic() - started, "billing_attested": False, "binding_authority": False}
    foundation.write_json(manifest_path, manifest); print(json.dumps(manifest, indent=2))


if __name__ == "__main__": main()