#!/usr/bin/env python3
"""Train a fresh QLoRA adapter natively on executable temporal programs."""

from __future__ import annotations

import argparse
import importlib.metadata
import json
import os
import random
import time
from pathlib import Path
from typing import Any

from program_common import read_jsonl, sha256_path, sha256_tree


def package_versions(names: list[str]) -> dict[str, str | None]:
    versions: dict[str, str | None] = {}
    for name in names:
        try:
            versions[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            versions[name] = None
    return versions


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--train-file", type=Path, required=True)
    parser.add_argument("--validation-file", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--resume")
    args = parser.parse_args()
    config = json.loads(args.config.read_text(encoding="utf-8"))
    rows = read_jsonl(args.train_file)
    if len(rows) != int(config["training_records"]):
        raise SystemExit("prepared training count differs from preregistration")
    exposures = int(config["effective_batch_size"]) * int(config["max_steps"])
    if exposures != int(config["registered_effective_sample_exposures"]):
        raise SystemExit("optimizer exposure count differs from preregistration")
    if exposures / len(rows) != float(config["epochs"]):
        raise SystemExit("registered epochs do not match effective sample exposures")
    versions = package_versions(list(config["required_packages"]))
    mismatches = {
        name: {"required": required, "actual": versions.get(name)}
        for name, required in config["required_packages"].items()
        if versions.get(name) != required
    }
    if mismatches:
        raise SystemExit("registered package mismatch: " + json.dumps(mismatches, sort_keys=True))

    import torch
    import torch.nn.functional as functional
    from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
    from torch.utils.data import Dataset
    from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig, Trainer, TrainingArguments

    if not torch.cuda.is_available():
        raise SystemExit("CUDA GPU required for Program-001 training")
    seed = int(config["training_seed"])
    random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)
    dtype = torch.bfloat16 if torch.cuda.is_bf16_supported() else torch.float16
    vram = torch.cuda.get_device_properties(0).total_memory / (1024 ** 3)
    tokenizer = AutoTokenizer.from_pretrained(
        config["model_name"], token=os.environ.get("HF_TOKEN"), revision=config["model_revision"]
    )
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    tokenizer.padding_side = "right"
    quantization = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_use_double_quant=True,
        bnb_4bit_compute_dtype=dtype,
    )
    model = AutoModelForCausalLM.from_pretrained(
        config["model_name"],
        token=os.environ.get("HF_TOKEN"),
        revision=config["model_revision"],
        dtype=dtype,
        quantization_config=quantization,
        device_map={"": 0},
    )
    model = prepare_model_for_kbit_training(model, use_gradient_checkpointing=True)
    lora = config["lora"]
    model = get_peft_model(model, LoraConfig(
        r=int(lora["r"]),
        lora_alpha=int(lora["alpha"]),
        lora_dropout=float(lora["dropout"]),
        target_modules=list(lora["target_modules"]),
        bias="none",
        task_type="CAUSAL_LM",
    ))
    model.config.use_cache = False
    max_length = int(config["max_length"])

    class CompletionDataset(Dataset):
        def __init__(self, source: list[dict[str, Any]]):
            self.rows = source
            full_lengths = []
            prompt_lengths = []
            completion_lengths = []
            for row in source:
                prompt = tokenizer(row["prompt"], add_special_tokens=False)["input_ids"]
                completion = tokenizer(row["completion"] + tokenizer.eos_token, add_special_tokens=False)["input_ids"]
                prompt_lengths.append(len(prompt))
                completion_lengths.append(len(completion))
                full_lengths.append(len(prompt) + len(completion))
            truncations = sum(length > max_length for length in full_lengths)
            limit = int(config["task_token_limits"]["TEMPORAL_PROGRAM"])
            limit_violations = sum(
                length + int(config["generation_token_margin"]) > limit
                for length in completion_lengths
            )
            if config["require_zero_training_truncation"] and truncations:
                raise ValueError(f"zero-truncation protocol violated for {truncations} records")
            if limit_violations:
                raise ValueError(f"generation limit too small for {limit_violations} records")
            self.audit = {
                "examples": len(source),
                "maximum_prompt_tokens": max(prompt_lengths),
                "maximum_completion_tokens": max(completion_lengths),
                "maximum_full_tokens": max(full_lengths),
                "prompt_truncation_examples": truncations,
                "generation_limit_violations": limit_violations,
                "max_length": max_length,
            }

        def __len__(self) -> int:
            return len(self.rows)

        def __getitem__(self, index: int) -> dict[str, Any]:
            row = self.rows[index]
            prompt_ids = tokenizer(row["prompt"], add_special_tokens=False)["input_ids"]
            completion_ids = tokenizer(row["completion"] + tokenizer.eos_token, add_special_tokens=False)["input_ids"]
            if len(prompt_ids) + len(completion_ids) > max_length:
                raise ValueError(f"zero-truncation violation: {row['case_id']}")
            return {
                "input_ids": prompt_ids + completion_ids,
                "attention_mask": [1] * (len(prompt_ids) + len(completion_ids)),
                "labels": [-100] * len(prompt_ids) + completion_ids,
                "sample_weight": float(row["sample_weight"]),
            }

    class Collator:
        def __call__(self, features: list[dict[str, Any]]) -> dict[str, Any]:
            width = max(len(item["input_ids"]) for item in features)
            return {
                "input_ids": torch.tensor([
                    item["input_ids"] + [tokenizer.pad_token_id] * (width - len(item["input_ids"]))
                    for item in features
                ]),
                "attention_mask": torch.tensor([
                    item["attention_mask"] + [0] * (width - len(item["attention_mask"]))
                    for item in features
                ]),
                "labels": torch.tensor([
                    item["labels"] + [-100] * (width - len(item["labels"]))
                    for item in features
                ]),
                "sample_weight": torch.tensor([item["sample_weight"] for item in features], dtype=torch.float32),
            }

    class WeightedTrainer(Trainer):
        def __init__(self, *items, **kwargs):
            super().__init__(*items, **kwargs)
            self.model_accepts_loss_kwargs = False

        def compute_loss(self, model, inputs, return_outputs=False, num_items_in_batch=None):
            labels = inputs.pop("labels")
            weights = inputs.pop("sample_weight").float()
            outputs = model(**inputs)
            logits = outputs.logits[..., :-1, :].contiguous()
            shifted = labels[..., 1:].contiguous()
            token_loss = functional.cross_entropy(
                logits.view(-1, logits.size(-1)), shifted.view(-1), ignore_index=-100, reduction="none"
            ).view(shifted.shape)
            mask = shifted.ne(-100)
            per_example = (token_loss * mask).sum(dim=1) / mask.sum(dim=1).clamp_min(1)
            loss = (per_example.float() * weights).mean()
            return (loss, outputs) if return_outputs else loss

    dataset = CompletionDataset(rows)
    args.output.mkdir(parents=True, exist_ok=True)
    training_args = TrainingArguments(
        output_dir=str(args.output),
        num_train_epochs=float(config["epochs"]),
        max_steps=int(config["max_steps"]),
        learning_rate=float(config["learning_rate"]),
        per_device_train_batch_size=int(config["per_device_train_batch_size"]),
        gradient_accumulation_steps=int(config["effective_batch_size"]) // int(config["per_device_train_batch_size"]),
        warmup_steps=int(config["warmup_steps"]),
        weight_decay=float(config["weight_decay"]),
        logging_steps=int(config["logging_steps"]),
        save_steps=int(config["save_steps"]),
        save_total_limit=2,
        bf16=dtype == torch.bfloat16,
        fp16=dtype == torch.float16,
        gradient_checkpointing=True,
        gradient_checkpointing_kwargs={"use_reentrant": False},
        report_to=[],
        remove_unused_columns=False,
        dataloader_drop_last=False,
        optim="paged_adamw_8bit",
        seed=seed,
        data_seed=seed,
    )
    trainer = WeightedTrainer(model=model, args=training_args, train_dataset=dataset, data_collator=Collator())
    started = time.time()
    result = trainer.train(resume_from_checkpoint=args.resume)
    final_adapter = args.output / "final-adapter"
    trainer.save_model(str(final_adapter))
    tokenizer.save_pretrained(str(final_adapter))
    trainable, total = model.get_nb_trainable_parameters()
    manifest = {
        "schema_version": "cerebrum-program-001-training-manifest.v1",
        "protocol_id": config["protocol_id"],
        "training_seed": seed,
        "base_model": config["model_name"],
        "base_model_revision": config["model_revision"],
        "fresh_adapter_from_base": True,
        "parent_adapter": None,
        "config_sha256": sha256_path(args.config),
        "train_sha256": sha256_path(args.train_file),
        "validation_sha256": sha256_path(args.validation_file),
        "final_adapter_sha256": sha256_tree(final_adapter),
        "training_records": len(rows),
        "registered_effective_sample_exposures": exposures,
        "registered_complete_dataset_passes": exposures / len(rows),
        "token_length_audit": dataset.audit,
        "trainable_parameters": trainable,
        "total_parameters": total,
        "elapsed_seconds": time.time() - started,
        "gpu": torch.cuda.get_device_name(0),
        "vram_gib": round(vram, 2),
        "max_steps": config["max_steps"],
        "metrics": result.metrics,
        "packages": package_versions(["torch", *config["required_packages"]]),
        "transfer_authorized": False,
        "binding_authority": False,
        "claim_boundary": "Fresh synthetic native-program QLoRA training only; no confirmed capability, transfer, deployment, authority, or IGI claim.",
    }
    (args.output / "training_manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(manifest, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())