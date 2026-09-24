#!/usr/bin/env python3
"""Checkpointed deterministic generation of constrained temporal programs."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any

from program_common import canonical, read_jsonl, sha256_path


def load_checkpoint(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows = []
    lines = path.read_bytes().splitlines()
    for index, line in enumerate(lines):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            if index != len(lines) - 1:
                raise
            break
        rows.append(row)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(canonical(row) + "\n" for row in rows), encoding="utf-8")
    return rows


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--adapter", type=Path)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    config = json.loads(args.config.read_text(encoding="utf-8"))
    rows = read_jsonl(args.input)
    existing = load_checkpoint(args.output)
    completed = {row.get("case_id") for row in existing}
    expected_ids = {row["case_id"] for row in rows}
    if None in completed or len(completed) != len(existing) or not completed.issubset(expected_ids):
        raise SystemExit("prediction checkpoint identifiers invalid")
    remaining = [row for row in rows if row["case_id"] not in completed]
    print(f"prediction checkpoint: completed={len(existing)} remaining={len(remaining)} total={len(rows)}", flush=True)
    if remaining:
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig

        if not torch.cuda.is_available():
            raise SystemExit("CUDA GPU required for Program-001 prediction")
        dtype = torch.bfloat16 if torch.cuda.is_bf16_supported() else torch.float16
        tokenizer = AutoTokenizer.from_pretrained(
            config["model_name"], token=os.environ.get("HF_TOKEN"), revision=config["model_revision"]
        )
        if tokenizer.pad_token is None:
            tokenizer.pad_token = tokenizer.eos_token
        quantization = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_use_double_quant=True,
            bnb_4bit_compute_dtype=dtype,
        )
        model = AutoModelForCausalLM.from_pretrained(
            config["model_name"], token=os.environ.get("HF_TOKEN"), revision=config["model_revision"],
            dtype=dtype, quantization_config=quantization, device_map={"": 0},
        )
        if args.adapter is not None:
            from peft import PeftModel
            model = PeftModel.from_pretrained(model, args.adapter)
        model.eval()
        token_limit = int(config["task_token_limits"]["TEMPORAL_PROGRAM"])
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open("a", encoding="utf-8", buffering=1) as checkpoint:
            for offset, row in enumerate(remaining, start=len(existing) + 1):
                prompt_tokens = tokenizer(row["prompt"], return_tensors="pt")
                prompt_count = int(prompt_tokens["input_ids"].shape[-1])
                if prompt_count > int(config["inference_max_input_tokens"]):
                    raise ValueError(f"prompt exceeds registered limit: {row['case_id']}")
                inputs = {key: value.to(model.device) for key, value in prompt_tokens.items()}
                with torch.no_grad():
                    generated = model.generate(
                        **inputs,
                        max_new_tokens=token_limit,
                        do_sample=False,
                        pad_token_id=tokenizer.eos_token_id,
                    )
                new_ids = generated[0, prompt_count:]
                raw = tokenizer.decode(new_ids, skip_special_tokens=True).strip()
                ended_with_eos = bool(len(new_ids) and int(new_ids[-1]) == tokenizer.eos_token_id)
                prediction = {
                    "case_id": row["case_id"],
                    "task_type": "TEMPORAL_PROGRAM",
                    "raw_output": raw,
                    "prompt_token_count": prompt_count,
                    "generated_token_count": len(new_ids),
                    "generation_token_limit": token_limit,
                    "ended_with_eos": ended_with_eos,
                    "hit_generation_limit": len(new_ids) >= token_limit and not ended_with_eos,
                }
                checkpoint.write(canonical(prediction) + "\n")
                checkpoint.flush()
                os.fsync(checkpoint.fileno())
                print(f"prediction progress: {offset}/{len(rows)} task=TEMPORAL_PROGRAM case={row['case_id']}", flush=True)
    predictions = load_checkpoint(args.output)
    if len(predictions) != len(rows):
        raise SystemExit(f"prediction checkpoint incomplete: {len(predictions)}/{len(rows)}")
    manifest = {
        "schema_version": "cerebrum-program-001-prediction-manifest.v1",
        "protocol_id": config["protocol_id"],
        "model": config["model_name"],
        "model_revision": config["model_revision"],
        "adapter": str(args.adapter) if args.adapter is not None else None,
        "input_sha256": sha256_path(args.input),
        "predictions_sha256": sha256_path(args.output),
        "count": len(predictions),
        "deterministic_decoding": True,
        "checkpointed_per_case": True,
        "resume_supported": True,
        "transfer_authorized": False,
        "binding_authority": False,
    }
    args.output.with_suffix(args.output.suffix + ".manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(manifest, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())