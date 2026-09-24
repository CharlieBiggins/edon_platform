#!/usr/bin/env python3
"""Freeze deterministic, compiled CEREBRUM-DEV-009 predictions."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any

from cerebrum_eventnet_data import ROOT, canonical, read_jsonl, sha256_path
from canonicalize import compile_prediction, valid_raw
from evaluate import parse_output


def load_checkpointed_predictions(path: Path) -> list[dict[str, Any]]:
    """Load complete JSONL rows and discard only a truncated trailing row."""
    if not path.exists():
        return []
    lines = path.read_bytes().splitlines()
    rows: list[dict[str, Any]] = []
    for index, line in enumerate(lines):
        if not line.strip():
            continue
        try:
            value = json.loads(line)
        except json.JSONDecodeError:
            if index != len(lines) - 1:
                raise ValueError(f"invalid non-trailing prediction row at line {index + 1}")
            break
        if not isinstance(value, dict):
            raise ValueError(f"prediction row {index + 1} is not an object")
        rows.append(value)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(canonical(row) + "\n" for row in rows), encoding="utf-8")
    return rows


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default="Qwen/Qwen3-4B-Instruct-2507")
    parser.add_argument("--config", type=Path, default=ROOT / "configs" / "qwen3-4b-multigen-repair.json")
    parser.add_argument("--adapter", type=Path)
    parser.add_argument("--input", type=Path, default=ROOT / "prepared" / "fresh-validation-all.jsonl")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--max-new-tokens", type=int)
    parser.add_argument("--load-in-4bit", action="store_true")
    args = parser.parse_args()
    config = json.loads(args.config.read_text(encoding="utf-8"))
    task_token_limits = {key: int(value) for key, value in config["task_token_limits"].items()}

    rows = read_jsonl(args.input)
    existing = load_checkpointed_predictions(args.output)
    completed = {row.get("case_id") for row in existing}
    expected_ids = {row["case_id"] for row in rows}
    if None in completed or len(completed) != len(existing):
        raise SystemExit("checkpoint contains missing or duplicate case IDs")
    if not completed.issubset(expected_ids):
        raise SystemExit("checkpoint contains cases absent from the requested input")
    remaining = [row for row in rows if row["case_id"] not in completed]
    print(f"prediction checkpoint: completed={len(existing)} remaining={len(remaining)} total={len(rows)}", flush=True)

    if remaining:
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig

        if not torch.cuda.is_available():
            raise SystemExit("CUDA GPU required for model prediction")
        model_revision = config.get("model_revision")
        tokenizer = AutoTokenizer.from_pretrained(
            args.model, token=os.environ.get("HF_TOKEN"), revision=model_revision
        )
        if tokenizer.pad_token is None:
            tokenizer.pad_token = tokenizer.eos_token
        dtype = torch.bfloat16 if torch.cuda.is_bf16_supported() else torch.float16
        quantization = None
        if args.load_in_4bit:
            quantization = BitsAndBytesConfig(
                load_in_4bit=True,
                bnb_4bit_quant_type="nf4",
                bnb_4bit_use_double_quant=True,
                bnb_4bit_compute_dtype=dtype,
            )
        model = AutoModelForCausalLM.from_pretrained(
            args.model,
            token=os.environ.get("HF_TOKEN"),
            revision=model_revision,
            dtype=dtype,
            quantization_config=quantization,
            device_map={"": 0},
        )
        if args.adapter:
            from peft import PeftModel
            model = PeftModel.from_pretrained(model, args.adapter)
        model.eval()
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open("a", encoding="utf-8", buffering=1) as checkpoint:
            for offset, row in enumerate(remaining, start=len(existing) + 1):
                prompt_token_count = len(tokenizer(row["prompt"], add_special_tokens=True)["input_ids"])
                input_limit = int(config["inference_max_input_tokens"])
                if prompt_token_count > input_limit:
                    raise ValueError(
                        f"inference prompt exceeds frozen limit for {row['case_id']}: {prompt_token_count}>{input_limit}"
                    )
                inputs = tokenizer(row["prompt"], return_tensors="pt").to(model.device)
                token_limit = args.max_new_tokens or task_token_limits[row["task_type"]]
                with torch.no_grad():
                    generated = model.generate(
                        **inputs,
                        max_new_tokens=token_limit,
                        do_sample=False,
                        return_dict_in_generate=True,
                        output_scores=True,
                        pad_token_id=tokenizer.eos_token_id,
                    )
                new_ids = generated.sequences[0, inputs["input_ids"].shape[-1] :]
                raw = tokenizer.decode(new_ids, skip_special_tokens=True).strip()
                parsed = parse_output(raw)
                compiled = compile_prediction(row["task_type"], row["compiler_input"], parsed)
                ended_with_eos = bool(len(new_ids) and int(new_ids[-1]) == tokenizer.eos_token_id)
                token_probabilities = [
                    float(torch.softmax(logits[0].float(), dim=-1)[token_id].item())
                    for token_id, logits in zip(new_ids, generated.scores)
                ]
                confidence = sum(token_probabilities) / len(token_probabilities) if token_probabilities else 0.0
                prediction = {
                    "case_id": row["case_id"],
                    "task_type": row["task_type"],
                    "raw_output": raw,
                    "parsed": parsed,
                    "raw_schema_valid": valid_raw(row["task_type"], parsed),
                    "compiled": compiled,
                    "compiled_output": canonical(compiled),
                    "prompt_token_count": prompt_token_count,
                    "generated_token_count": len(new_ids),
                    "generation_token_limit": token_limit,
                    "ended_with_eos": ended_with_eos,
                    "hit_generation_limit": len(new_ids) >= token_limit and not ended_with_eos,
                    "confidence": confidence,
                }
                checkpoint.write(canonical(prediction) + "\n")
                checkpoint.flush()
                os.fsync(checkpoint.fileno())
                print(f"prediction progress: {offset}/{len(rows)} task={row['task_type']} case={row['case_id']}", flush=True)
    predictions = load_checkpointed_predictions(args.output)
    if len(predictions) != len(rows):
        raise SystemExit(f"prediction checkpoint incomplete: {len(predictions)}/{len(rows)}")
    manifest = {
        "schema_version": "cerebrum-execution-repair-prediction-manifest.v1",
        "protocol_id": "CEREBRUM-DEV-009",
        "model": args.model,
        "model_revision": config.get("model_revision"),
        "adapter": str(args.adapter) if args.adapter else None,
        "input_sha256": sha256_path(args.input),
        "predictions_sha256": sha256_path(args.output),
        "count": len(predictions),
        "task_counts": {task: sum(row["task_type"] == task for row in rows) for task in task_token_limits},
        "task_token_limits": task_token_limits,
        "inference_max_input_tokens": config["inference_max_input_tokens"],
        "deterministic_compiler": True,
        "hashes_derived_from_model_predicted_states": True,
        "deterministic_decoding": True,
        "checkpointed_per_case": True,
        "resume_supported": True,
        "public_scored": False,
        "binding_authority": False,
    }
    manifest_path = args.output.with_suffix(args.output.suffix + ".manifest.json")
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(manifest, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())