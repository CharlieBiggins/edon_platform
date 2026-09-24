#!/usr/bin/env python3
"""Length-safe weighted single-GPU QLoRA trainer for CEREBRUM-DEV-009."""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import os
import random
import time
from collections import Counter
from pathlib import Path
from typing import Any

from cerebrum_eventnet_data import ROOT, read_jsonl, sha256_path


def load_config(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def package_versions(names: list[str]) -> dict[str, str | None]:
    versions: dict[str, str | None] = {}
    for name in names:
        try:
            versions[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            versions[name] = None
    return versions


def summarize_rows(rows: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "records": len(rows),
        "task_counts": dict(sorted(Counter(row["task_type"] for row in rows).items())),
        "weight_sum": round(sum(float(row["sample_weight"]) for row in rows), 6),
        "weight_min": min(float(row["sample_weight"]) for row in rows),
        "weight_max": max(float(row["sample_weight"]) for row in rows),
    }


def stratified_rows(rows: list[dict[str, Any]], limit: int | None) -> list[dict[str, Any]]:
    """Select a deterministic smoke subset that exercises every available task."""
    if limit is None or limit >= len(rows):
        return rows
    registered_order = ("CERTIFICATE", "TRANSITION", "QUEUE_TRACE", "PAIR_CONTRAST")
    tasks = [task for task in registered_order if any(row["task_type"] == task for row in rows)]
    tasks.extend(sorted({row["task_type"] for row in rows} - set(tasks)))
    base, remainder = divmod(limit, len(tasks))
    buckets = {
        task: [row for row in rows if row["task_type"] == task][: base + int(index < remainder)]
        for index, task in enumerate(tasks)
    }
    selected: list[dict[str, Any]] = []
    for index in range(max(len(bucket) for bucket in buckets.values())):
        for task in tasks:
            if index < len(buckets[task]):
                selected.append(buckets[task][index])
    if len(selected) != limit:
        raise ValueError(f"stratified selection produced {len(selected)} rows instead of {limit}")
    return selected


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=ROOT / "configs" / "qwen3-4b-multigen-repair.json")
    parser.add_argument("--condition", default="multi_generator_execution_repair")
    parser.add_argument("--seed", type=int)
    parser.add_argument("--train-file", type=Path)
    parser.add_argument("--validation-file", type=Path, default=ROOT / "prepared" / "fresh-validation-all.jsonl")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--epochs", type=float)
    parser.add_argument("--max-steps", type=int, default=-1)
    parser.add_argument("--limit-train-examples", type=int)
    parser.add_argument("--smoke-test", action="store_true")
    parser.add_argument("--resume")
    args = parser.parse_args()
    config = load_config(args.config)
    if args.condition not in config["condition_files"]:
        raise SystemExit(f"unknown registered condition: {args.condition}")
    seed = args.seed if args.seed is not None else config["registered_seeds"][0]
    if not args.smoke_test and seed not in config["registered_seeds"]:
        raise SystemExit(f"seed {seed} is not registered: {config['registered_seeds']}")
    train_file = args.train_file or ROOT / config["condition_files"][args.condition]
    condition = "smoke_test" if args.smoke_test else args.condition
    output = args.output or ROOT / "artifacts" / (
        f"smoke-{args.condition}-seed-{seed}" if args.smoke_test else f"{args.condition}-seed-{seed}"
    )
    epochs = args.epochs if args.epochs is not None else config["epochs"]
    max_steps = 3 if args.smoke_test and args.max_steps == -1 else args.max_steps
    limit = 24 if args.smoke_test and args.limit_train_examples is None else args.limit_train_examples
    if not train_file.exists() or not args.validation_file.exists():
        raise SystemExit("prepared repair data missing; run python prepare_data.py")
    rows = read_jsonl(train_file)
    if not args.smoke_test and len(rows) != config["registered_condition_counts"][args.condition]:
        raise SystemExit("prepared condition count differs from preregistration")

    import torch
    import torch.nn.functional as functional
    from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
    from torch.utils.data import Dataset
    from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig, Trainer, TrainingArguments

    if not torch.cuda.is_available():
        raise SystemExit("CUDA GPU required for training; CPU is supported only for preparation and preflight")
    random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)
    vram = torch.cuda.get_device_properties(0).total_memory / (1024 ** 3)
    max_length = int(config["max_length"])
    batch_size = 1 if vram < 32 else config["per_device_train_batch_size"]
    gradient_accumulation = max(1, config["effective_batch_size"] // batch_size)
    compute_dtype = torch.bfloat16 if torch.cuda.is_bf16_supported() else torch.float16

    model_revision = config.get("model_revision")
    tokenizer = AutoTokenizer.from_pretrained(
        config["model_name"], token=os.environ.get("HF_TOKEN"), revision=model_revision
    )
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    tokenizer.padding_side = "right"
    quantization = None
    if config["load_in_4bit"]:
        quantization = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_use_double_quant=True,
            bnb_4bit_compute_dtype=compute_dtype,
        )
    model = AutoModelForCausalLM.from_pretrained(
        config["model_name"],
        token=os.environ.get("HF_TOKEN"),
        revision=model_revision,
        dtype=compute_dtype,
        quantization_config=quantization,
        device_map={"": 0},
    )
    if quantization is not None:
        model = prepare_model_for_kbit_training(model, use_gradient_checkpointing=True)
    model.config.use_cache = False
    model = get_peft_model(model, LoraConfig(
        r=config["lora_r"],
        lora_alpha=config["lora_alpha"],
        lora_dropout=config["lora_dropout"],
        target_modules=config["target_modules"],
        bias="none",
        task_type="CAUSAL_LM",
    ))

    class CompletionDataset(Dataset):
        def __init__(self, source_rows: list[dict[str, Any]], row_limit: int | None = None):
            self.rows = stratified_rows(source_rows, row_limit)
            self.weight_normalizer = sum(float(row["sample_weight"]) for row in self.rows) / len(self.rows)
            full_lengths: list[int] = []
            completion_lengths: list[int] = []
            completion_lengths_by_task: dict[str, list[int]] = {}
            for row in self.rows:
                prompt_length = len(tokenizer(row["prompt"], add_special_tokens=False)["input_ids"])
                completion_length = len(tokenizer(row["completion"] + tokenizer.eos_token, add_special_tokens=False)["input_ids"])
                if completion_length >= max_length:
                    raise ValueError(f"completion exceeds max_length for {row['case_id']}")
                full_lengths.append(prompt_length + completion_length)
                completion_lengths.append(completion_length)
                completion_lengths_by_task.setdefault(row["task_type"], []).append(completion_length)
            truncation_examples = sum(length > max_length for length in full_lengths)
            if config.get("require_zero_training_truncation") and truncation_examples:
                raise ValueError(
                    f"zero-truncation protocol violated: {truncation_examples}/{len(self.rows)} examples exceed {max_length} tokens"
                )
            task_max_completion_tokens = {
                task: max(lengths) for task, lengths in sorted(completion_lengths_by_task.items())
            }
            margin = int(config["generation_token_margin"])
            for task, maximum in task_max_completion_tokens.items():
                if int(config["task_token_limits"][task]) < maximum + margin:
                    raise ValueError(
                        f"generation limit too small for {task}: {config['task_token_limits'][task]} < {maximum}+{margin}"
                    )
            self.token_length_audit = {
                "examples": len(self.rows),
                "max_full_tokens": max(full_lengths),
                "max_completion_tokens": max(completion_lengths),
                "prompt_truncation_examples": truncation_examples,
                "task_max_completion_tokens": task_max_completion_tokens,
                "task_generation_limits": config["task_token_limits"],
                "generation_token_margin": margin,
                "max_length": max_length,
            }

        def __len__(self) -> int:
            return len(self.rows)

        def __getitem__(self, index: int) -> dict[str, Any]:
            row = self.rows[index]
            prompt_ids = tokenizer(row["prompt"], add_special_tokens=False)["input_ids"]
            completion_ids = tokenizer(row["completion"] + tokenizer.eos_token, add_special_tokens=False)["input_ids"]
            if len(completion_ids) >= max_length:
                raise ValueError(f"completion exceeds max_length for {row['case_id']}")
            if len(prompt_ids) + len(completion_ids) > max_length:
                raise ValueError(f"zero-truncation protocol violated for {row['case_id']}")
            input_ids = prompt_ids + completion_ids
            labels = [-100] * len(prompt_ids) + completion_ids
            return {
                "input_ids": input_ids,
                "attention_mask": [1] * len(input_ids),
                "labels": labels,
                "sample_weight": float(row["sample_weight"]),
            }

    class Collator:
        def __call__(self, features: list[dict[str, Any]]) -> dict[str, Any]:
            width = max(len(item["input_ids"]) for item in features)
            input_ids, masks, labels, weights = [], [], [], []
            for item in features:
                pad = width - len(item["input_ids"])
                input_ids.append(item["input_ids"] + [tokenizer.pad_token_id] * pad)
                masks.append(item["attention_mask"] + [0] * pad)
                labels.append(item["labels"] + [-100] * pad)
                weights.append(item["sample_weight"])
            return {
                "input_ids": torch.tensor(input_ids, dtype=torch.long),
                "attention_mask": torch.tensor(masks, dtype=torch.long),
                "labels": torch.tensor(labels, dtype=torch.long),
                "sample_weight": torch.tensor(weights, dtype=torch.float32),
            }

    class WeightedCompletionTrainer(Trainer):
        def __init__(self, *trainer_args, weight_normalizer: float, **trainer_kwargs):
            super().__init__(*trainer_args, **trainer_kwargs)
            self.weight_normalizer = weight_normalizer
            # This custom loss does not consume num_items_in_batch. Let Trainer
            # apply the normal gradient-accumulation scaling exactly once.
            self.model_accepts_loss_kwargs = False

        def compute_loss(self, model, inputs, return_outputs=False, num_items_in_batch=None):
            labels = inputs.pop("labels")
            weights = inputs.pop("sample_weight").to(dtype=torch.float32)
            outputs = model(**inputs)
            shift_logits = outputs.logits[..., :-1, :].contiguous()
            shift_labels = labels[..., 1:].contiguous()
            token_loss = functional.cross_entropy(
                shift_logits.view(-1, shift_logits.size(-1)),
                shift_labels.view(-1),
                ignore_index=-100,
                reduction="none",
            ).view(shift_labels.shape)
            mask = shift_labels.ne(-100)
            per_example = (token_loss * mask).sum(dim=1) / mask.sum(dim=1).clamp_min(1)
            # Normalize by the dataset-wide mean weight rather than the current
            # microbatch. On the L4 the microbatch is one, so microbatch-local
            # normalization would cancel every sample weight.
            loss = (per_example.float() * weights).mean() / self.weight_normalizer
            return (loss, outputs) if return_outputs else loss

    output.mkdir(parents=True, exist_ok=True)
    training_args = TrainingArguments(
        output_dir=str(output),
        num_train_epochs=epochs,
        max_steps=max_steps,
        learning_rate=config["learning_rate"],
        per_device_train_batch_size=batch_size,
        gradient_accumulation_steps=gradient_accumulation,
        warmup_steps=config["warmup_steps"],
        weight_decay=config["weight_decay"],
        logging_steps=config["logging_steps"],
        save_steps=config["save_steps"],
        save_total_limit=2,
        bf16=compute_dtype == torch.bfloat16,
        fp16=compute_dtype == torch.float16,
        gradient_checkpointing=True,
        gradient_checkpointing_kwargs={"use_reentrant": False},
        report_to=[],
        remove_unused_columns=False,
        optim="paged_adamw_8bit" if config["load_in_4bit"] else "adamw_torch",
        seed=seed,
        data_seed=seed,
    )
    train_dataset = CompletionDataset(rows, limit)
    trainer = WeightedCompletionTrainer(
        model=model,
        args=training_args,
        train_dataset=train_dataset,
        data_collator=Collator(),
        weight_normalizer=train_dataset.weight_normalizer,
    )
    started = time.time()
    train_result = trainer.train(resume_from_checkpoint=args.resume)
    adapter_path = output / "final-adapter"
    trainer.save_model(str(adapter_path))
    tokenizer.save_pretrained(str(adapter_path))
    trainable, total = model.get_nb_trainable_parameters()
    manifest = {
        "schema_version": "cerebrum-execution-repair-training-manifest.v1",
        "protocol_id": "CEREBRUM-DEV-009",
        "condition": condition,
        "registered_condition": args.condition,
        "seed": seed,
        "base_model": config["model_name"],
        "base_model_revision": model_revision,
        "config_sha256": sha256_path(args.config),
        "train_sha256": sha256_path(train_file),
        "validation_sha256": sha256_path(args.validation_file),
        "adapter_path": "final-adapter",
        "weighted_completion_loss": True,
        "weight_normalizer": train_dataset.weight_normalizer,
        "trainer_scales_gradient_accumulation": True,
        "training_data": summarize_rows(train_dataset.rows),
        "token_length_audit": train_dataset.token_length_audit,
        "trainable_parameters": trainable,
        "total_parameters": total,
        "elapsed_seconds": time.time() - started,
        "gpu": torch.cuda.get_device_name(0),
        "vram_gib": round(vram, 2),
        "max_length": max_length,
        "inference_max_input_tokens": config["inference_max_input_tokens"],
        "zero_training_truncation_required": config["require_zero_training_truncation"],
        "per_device_batch": batch_size,
        "gradient_accumulation": gradient_accumulation,
        "epochs": epochs,
        "max_steps": max_steps,
        "smoke_test": args.smoke_test,
        "metrics": train_result.metrics,
        "packages": package_versions(["torch", "transformers", "peft", "accelerate", "bitsandbytes"]),
        "model_lineage": "model-" + hashlib.sha256(
            f"{config['model_name']}:{args.condition}:{seed}:{sha256_path(train_file)}".encode("utf-8")
        ).hexdigest()[:20],
        "public_scored": False,
        "binding_authority": False,
        "claim_boundary": "Fresh-lineage internal synthetic EventNet repair LoRA with deterministic canonical compilation; no public, protected, real-institution, autonomous-authority, or production claim.",
    }
    (output / "training_manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(manifest, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())