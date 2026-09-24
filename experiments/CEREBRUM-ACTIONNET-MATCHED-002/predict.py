"""Explicit paid inference for one frozen Matched-002 candidate."""
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
    if path.is_absolute() or PureWindowsPath(str(path)).drive:
        raise argparse.ArgumentTypeError("Use relative paths")
    return path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", type=relative, required=True)
    parser.add_argument("--candidate", choices=CANDIDATES, required=True)
    parser.add_argument("--candidate-run", type=relative, required=True)
    parser.add_argument("--arm", choices=("ordinary", "actionnet"), required=True)
    parser.add_argument("--base-snapshot", type=relative, required=True)
    parser.add_argument("--authorize-paid", action="store_true")
    args = parser.parse_args()
    if not args.authorize_paid:
        raise ValueError("Paid inference requires literal --authorize-paid")
    sys.path.insert(0, str(MATCHED001))
    import foundation
    import gpu_worker
    expected_label, expected_arm = CANDIDATES[args.candidate]
    foundation.require(args.arm == expected_arm, "Candidate arm differs")
    study002 = foundation.read(args.run_dir / "study.json")
    foundation.require(study002["execution"]["paid_execution_approved"] is True,
                       "Study has no paid inference approval")
    commitments = foundation.read(args.run_dir / "candidate-commitments.json")
    foundation.require(foundation.file_hash(args.candidate_run / "registration.json")
        == commitments[args.candidate]["registration_sha256"], "Candidate registration differs")
    study001 = foundation.read(args.candidate_run / "study.json")
    config001 = foundation.read(MATCHED001 / "config.json")
    foundation.require(study001["training_seed_label"] == expected_label, "Candidate seed differs")
    hashes = foundation.snapshot_hashes(args.base_snapshot)
    foundation.require(hashes["weights_tree_sha256"] == study001["base_snapshot"]["weights_tree_sha256"]
        and hashes["tokenizer_tree_sha256"] == study001["base_snapshot"]["tokenizer_tree_sha256"],
        "Base snapshot differs")
    trained = gpu_worker.trained_manifest(args.candidate_run, args.arm, config001)
    inputs = foundation.rows(args.run_dir / "qualification-inputs.jsonl", "case_id")
    output = args.run_dir / "results" / (args.candidate + "-predictions.jsonl")
    manifest_path = output.with_suffix(".manifest.json")
    if manifest_path.exists():
        print(json.dumps(foundation.read(manifest_path), indent=2)); return
    output.parent.mkdir(parents=True, exist_ok=True)
    existing = foundation.rows(output, "case_id") if output.exists() else []
    foundation.require([row["case_id"] for row in existing]
        == [row["case_id"] for row in inputs[:len(existing)]], "Prediction prefix differs")
    torch, _ = gpu_worker.runtime_environment(config001)
    from peft import PeftModel
    base, tokenizer, _ = gpu_worker.load_base(torch, args.base_snapshot)
    model = PeftModel.from_pretrained(base, str(args.candidate_run / "artifacts" / args.arm / "adapter"))
    model.eval(); started = time.monotonic()
    cap = study002["execution"]["maximum_total_gpu_hours"] * 3600 / 4
    with output.open("ab") as stream:
        for index, value in enumerate(inputs[len(existing):], start=len(existing) + 1):
            foundation.require(time.monotonic() - started <= cap, "Per-candidate inference cap reached")
            encoded = tokenizer(value["prompt"], return_tensors="pt", add_special_tokens=False)
            length = int(encoded["input_ids"].shape[-1]); one = time.monotonic()
            with torch.no_grad():
                generated = model.generate(**{key: item.to(model.device) for key, item in encoded.items()},
                    max_new_tokens=config001["max_new_tokens"], do_sample=False,
                    pad_token_id=tokenizer.pad_token_id, eos_token_id=tokenizer.eos_token_id)
            tokens = generated[0, length:]
            ended = bool(len(tokens) and int(tokens[-1]) == tokenizer.eos_token_id)
            row = {"case_id": value["case_id"],
                "raw_output": tokenizer.decode(tokens, skip_special_tokens=True).strip(),
                "ended_with_eos": ended,
                "hit_generation_limit": len(tokens) >= config001["max_new_tokens"] and not ended,
                "prompt_token_count": length, "generated_token_count": len(tokens),
                "generation_seconds": time.monotonic() - one}
            stream.write((json.dumps(row, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n").encode())
            stream.flush(); os.fsync(stream.fileno()); print(f"{args.candidate}: {index}/48", flush=True)
    manifest = {"protocol_id": "CEREBRUM-ACTIONNET-MATCHED-002", "candidate": args.candidate,
        "candidate_registration_sha256": foundation.file_hash(args.candidate_run / "registration.json"),
        "training_manifest_sha256": foundation.file_hash(args.candidate_run / "artifacts" / args.arm / "training.json"),
        "adapter_sha256": trained["adapter_sha256"], "count": 48,
        "predictions_sha256": foundation.file_hash(output), "gpu_seconds": time.monotonic() - started,
        "billing_attested": False, "binding_authority": False}
    foundation.write_json(manifest_path, manifest)
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()