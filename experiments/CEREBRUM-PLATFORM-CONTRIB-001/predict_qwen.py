#!/usr/bin/env python3
"""Freeze label-free protected predictions from one trained adapter."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


BASE_MODEL = "Qwen/Qwen3-4B-Instruct-2507"


def parse_json(text: str) -> dict:
    candidate = text.strip()
    if candidate.startswith("```"):
        candidate = candidate.split("\n", 1)[1].rsplit("```", 1)[0].strip()
    start = candidate.find("{")
    end = candidate.rfind("}")
    if start < 0 or end < start:
        return {"parse_error": True, "raw_output": text, "binding_authority": False}
    try:
        value = json.loads(candidate[start:end + 1])
    except json.JSONDecodeError:
        return {"parse_error": True, "raw_output": text, "binding_authority": False}
    if not isinstance(value, dict):
        return {"parse_error": True, "raw_output": text, "binding_authority": False}
    value["binding_authority"] = False
    return value


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--adapter", type=Path, required=True)
    parser.add_argument("--model", default=BASE_MODEL)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        import torch
        from peft import PeftModel
        from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
    except ImportError as exc:
        raise SystemExit(f"missing external inference dependency: {exc}")
    if not torch.cuda.is_available():
        raise SystemExit("CUDA GPU is required for registered Qwen prediction")
    root = Path(__file__).resolve().parent
    inputs = [
        json.loads(line) for line in (root / "protected" / "public_inputs.jsonl").read_text().splitlines()
        if line
    ]
    tokenizer = AutoTokenizer.from_pretrained(args.model, trust_remote_code=True)
    quantization = BitsAndBytesConfig(
        load_in_4bit=True, bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=torch.bfloat16, bnb_4bit_use_double_quant=True,
    )
    base = AutoModelForCausalLM.from_pretrained(
        args.model, quantization_config=quantization, device_map="auto", trust_remote_code=True
    )
    model = PeftModel.from_pretrained(base, args.adapter)
    model.eval()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8") as handle:
        for row in inputs:
            prompt = tokenizer.apply_chat_template(
                row["messages"], tokenize=False, add_generation_prompt=True
            )
            encoded = tokenizer(prompt, return_tensors="pt").to(model.device)
            with torch.inference_mode():
                generated = model.generate(
                    **encoded, max_new_tokens=256, do_sample=False,
                    pad_token_id=tokenizer.eos_token_id,
                )
            completion = tokenizer.decode(
                generated[0][encoded["input_ids"].shape[1]:], skip_special_tokens=True
            )
            handle.write(json.dumps({
                "case_id": row["case_id"], "prediction": parse_json(completion)
            }, sort_keys=True) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())