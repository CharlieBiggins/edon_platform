#!/usr/bin/env python3
"""Train one frozen Qwen QLoRA contribution condition on an external GPU."""

from __future__ import annotations

import argparse
import json
import random
from pathlib import Path


BASE_MODEL = "Qwen/Qwen3-4B-Instruct-2507"
ALLOWED_SEEDS = {26082341, 26082342}
CONDITIONS = {"control", "platform002"}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--condition", choices=sorted(CONDITIONS), required=True)
    parser.add_argument("--seed", type=int, choices=sorted(ALLOWED_SEEDS), required=True)
    parser.add_argument("--model", default=BASE_MODEL)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()

    try:
        import torch
        from datasets import Dataset
        from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
        from transformers import (
            AutoModelForCausalLM,
            AutoTokenizer,
            BitsAndBytesConfig,
            Trainer,
            TrainingArguments,
        )
    except ImportError as exc:
        raise SystemExit(f"missing external GPU training dependency: {exc}")
    if not torch.cuda.is_available():
        raise SystemExit("CUDA GPU is required for the registered QLoRA execution")

    root = Path(__file__).resolve().parent
    rows = [
        json.loads(line) for line in (root / "training" / f"{args.condition}.jsonl").read_text().splitlines()
        if line
    ]
    random.Random(args.seed).shuffle(rows)
    tokenizer = AutoTokenizer.from_pretrained(args.model, trust_remote_code=True)
    if tokenizer.pad_token_id is None:
        tokenizer.pad_token = tokenizer.eos_token
    max_length = 2048

    def encode(row):
        messages = row["messages"]
        prompt_text = tokenizer.apply_chat_template(
            messages[:-1], tokenize=False, add_generation_prompt=True
        )
        full_text = tokenizer.apply_chat_template(messages, tokenize=False)
        prompt_ids = tokenizer(prompt_text, add_special_tokens=False)["input_ids"]
        encoded = tokenizer(
            full_text, add_special_tokens=False, truncation=True, max_length=max_length
        )
        labels = [-100] * min(len(prompt_ids), len(encoded["input_ids"]))
        labels += encoded["input_ids"][len(labels):]
        return {
            "input_ids": encoded["input_ids"],
            "attention_mask": encoded["attention_mask"],
            "labels": labels,
        }

    dataset = Dataset.from_list(rows).map(encode, remove_columns=list(rows[0]))

    class Collator:
        def __call__(self, features):
            width = max(len(row["input_ids"]) for row in features)
            def padded(key, fill):
                return torch.tensor(
                    [row[key] + [fill] * (width - len(row[key])) for row in features],
                    dtype=torch.long,
                )
            return {
                "input_ids": padded("input_ids", tokenizer.pad_token_id),
                "attention_mask": padded("attention_mask", 0),
                "labels": padded("labels", -100),
            }

    quantization = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=torch.bfloat16,
        bnb_4bit_use_double_quant=True,
    )
    model = AutoModelForCausalLM.from_pretrained(
        args.model, quantization_config=quantization, device_map="auto", trust_remote_code=True
    )
    model = prepare_model_for_kbit_training(model)
    model = get_peft_model(model, LoraConfig(
        r=16, lora_alpha=32, lora_dropout=0.05, bias="none", task_type="CAUSAL_LM",
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"],
    ))
    args.output_dir.mkdir(parents=True, exist_ok=True)
    training_args = TrainingArguments(
        output_dir=str(args.output_dir), num_train_epochs=2,
        per_device_train_batch_size=1, gradient_accumulation_steps=16,
        learning_rate=2e-4, warmup_ratio=0.05, logging_steps=10,
        save_strategy="epoch", bf16=True, gradient_checkpointing=True,
        seed=args.seed, data_seed=args.seed, report_to="none",
        remove_unused_columns=False,
    )
    trainer = Trainer(
        model=model, args=training_args, train_dataset=dataset,
        data_collator=Collator(),
    )
    trainer.train()
    model.save_pretrained(args.output_dir / "adapter")
    tokenizer.save_pretrained(args.output_dir / "adapter")
    manifest = {
        "schema_version": "cerebrum-platform-contrib-adapter.v1",
        "condition": args.condition, "seed": args.seed, "base_model": args.model,
        "training_records": len(rows), "binding_authority": False,
    }
    (args.output_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())