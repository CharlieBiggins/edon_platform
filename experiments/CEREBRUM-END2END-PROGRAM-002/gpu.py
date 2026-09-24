"""Explicit GPU workers. No package installation, deployment, or output repair."""
from __future__ import annotations

import argparse
import importlib.metadata
import json
import os
import random

from common import (ROOT, config, verify_freeze, file_hash, tree_hash, read_json,
                    read_rows, write_json, canonical)
from loss import encode_row


def runtime():
    cfg = config()
    versions = {name: importlib.metadata.version(name) for name in cfg["required_packages"]}
    if versions != cfg["required_packages"]:
        raise ValueError(f"registered runtime mismatch: {versions}")
    import torch
    if not torch.cuda.is_available():
        raise ValueError("CUDA GPU required; CPU qualification is not GPU readiness")
    if int(os.environ.get("WORLD_SIZE", "1")) != 1:
        raise ValueError("single-GPU training only")
    return torch, versions


def load_base(torch):
    from transformers import AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig
    cfg = config()
    dtype = torch.bfloat16 if torch.cuda.is_bf16_supported() else torch.float16
    tokenizer = AutoTokenizer.from_pretrained(cfg["model_name"], revision=cfg["model_revision"],
                                             token=os.environ.get("HF_TOKEN"), use_fast=True)
    if not tokenizer.is_fast:
        raise ValueError("fast tokenizer required for structural token offsets")
    if tokenizer.pad_token_id is None:
        tokenizer.pad_token = tokenizer.eos_token
    tokenizer.padding_side = "right"
    model = AutoModelForCausalLM.from_pretrained(
        cfg["model_name"], revision=cfg["model_revision"], token=os.environ.get("HF_TOKEN"),
        dtype=dtype, device_map={"": 0},
        quantization_config=BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_quant_type="nf4",
                                              bnb_4bit_use_double_quant=True,
                                              bnb_4bit_compute_dtype=dtype))
    return model, tokenizer, dtype


def train(arm):
    verify_freeze()
    cfg = config()
    if arm not in cfg["arms"]:
        raise ValueError("unregistered arm")
    out = ROOT / "artifacts" / arm
    completed = out / "training.json"
    if completed.exists():
        trained_manifest(arm)
        return
    if (ROOT / "results/selection.json").exists():
        raise ValueError("training is closed after development selection")
    torch, versions = runtime()
    from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
    from transformers import Trainer, TrainingArguments
    from transformers.trainer_utils import get_last_checkpoint
    import torch.nn.functional as functional
    seed = cfg["training_seed"]
    random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)
    binding = {"arm": arm, "registration_sha256": file_hash(ROOT / "registration.json"),
               "train_sha256": file_hash(ROOT / "prepared/train.jsonl"), "packages": versions}
    write_json(out / "start.json", binding)
    model, tokenizer, dtype = load_base(torch)
    # Check every train/development length before training; confirmation stays unmaterialized.
    rows = read_rows(ROOT / "prepared/train.jsonl")
    encoded = [encode_row(row, tokenizer, cfg, arm) for row in rows]
    dev = [encode_row(row, tokenizer, cfg, arm) for row in read_rows(ROOT / "prepared/development.jsonl")]
    write_json(out / "token-audit.json", {
        "train_records": len(encoded), "development_records": len(dev),
        "maximum_train_tokens": max(len(row["input_ids"]) for row in encoded),
        "maximum_development_tokens": max(len(row["input_ids"]) for row in dev),
        "truncations": 0, "target_budget_violations": 0})
    model = prepare_model_for_kbit_training(model, use_gradient_checkpointing=True)
    lora = cfg["lora"]
    model = get_peft_model(model, LoraConfig(r=lora["r"], lora_alpha=lora["alpha"],
        lora_dropout=lora["dropout"], target_modules=lora["target_modules"],
        bias="none", task_type="CAUSAL_LM"))
    model.config.use_cache = False

    def collate(features):
        width = max(len(row["input_ids"]) for row in features)
        pads = {"input_ids": tokenizer.pad_token_id, "attention_mask": 0,
                "labels": -100, "token_weights": 0.0}
        return {key: torch.tensor([row[key] + [pad] * (width - len(row[key])) for row in features],
                                 dtype=torch.float32 if key == "token_weights" else torch.long)
                for key, pad in pads.items()}

    class StructuralTrainer(Trainer):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.model_accepts_loss_kwargs = False

        def compute_loss(self, model, inputs, return_outputs=False, num_items_in_batch=None):
            labels = inputs.pop("labels")[:, 1:].contiguous()
            weights = inputs.pop("token_weights")[:, 1:].contiguous()
            outputs = model(**inputs)
            logits = outputs.logits[:, :-1, :].contiguous()
            losses = functional.cross_entropy(logits.view(-1, logits.size(-1)), labels.view(-1),
                                             ignore_index=-100, reduction="none").view(labels.shape)
            weights = weights * labels.ne(-100)
            # Normalize within each example so the intervention changes allocation, not loss scale.
            loss = ((losses * weights).sum(1) / weights.sum(1).clamp_min(1)).mean()
            return (loss, outputs) if return_outputs else loss

    args = TrainingArguments(
        output_dir=str(out / "checkpoints"), max_steps=cfg["max_steps"], num_train_epochs=cfg["epochs"],
        per_device_train_batch_size=1, gradient_accumulation_steps=cfg["effective_batch_size"],
        learning_rate=cfg["learning_rate"], warmup_steps=cfg["warmup_steps"],
        weight_decay=cfg["weight_decay"], save_steps=64, save_total_limit=2, logging_steps=4,
        bf16=dtype == torch.bfloat16, fp16=dtype == torch.float16,
        gradient_checkpointing=True, gradient_checkpointing_kwargs={"use_reentrant": False},
        report_to=[], remove_unused_columns=False, optim="paged_adamw_8bit",
        seed=seed, data_seed=seed, dataloader_drop_last=False)
    trainer = StructuralTrainer(model=model, args=args, train_dataset=encoded, data_collator=collate)
    checkpoints = out / "checkpoints"
    last = get_last_checkpoint(str(checkpoints)) if checkpoints.exists() else None
    trainer.train(resume_from_checkpoint=last)
    if trainer.state.global_step != cfg["max_steps"]:
        raise ValueError("training did not reach the registered final step")
    adapter = out / "adapter"
    trainer.save_model(str(adapter))
    tokenizer.save_pretrained(str(adapter))
    write_json(completed, {**binding, "step": trainer.state.global_step,
                           "fresh_adapter_from_base": True, "parent_adapter": None,
                           "adapter_sha256": tree_hash(adapter),
                           "gpu": torch.cuda.get_device_name(0), "dtype": str(dtype),
                           "torch_version": torch.__version__, "binding_authority": False,
                           "transfer_authorized": False})


def trained_manifest(arm):
    verify_freeze()
    if arm not in config()["arms"]:
        raise ValueError("unregistered arm")
    out = ROOT / "artifacts" / arm
    manifest = read_json(out / "training.json")
    if manifest["registration_sha256"] != file_hash(ROOT / "registration.json"):
        raise ValueError("adapter belongs to another registration")
    if manifest["step"] != config()["max_steps"] or manifest["adapter_sha256"] != tree_hash(out / "adapter"):
        raise ValueError("adapter changed or wrong checkpoint")
    return manifest


def predict(arm, split):
    cfg = config()
    trained = trained_manifest(arm)
    if split not in ("development", "confirmation"):
        raise ValueError("unregistered evaluation split")
    if split == "confirmation":
        from run import require_confirmation_access
        require_confirmation_access()
    source = ROOT / f"prepared/{split}.jsonl"
    rows = read_rows(source)
    if len(rows) != cfg["splits"][split]["records"]:
        raise ValueError("evaluation count mismatch")
    path = ROOT / f"results/{split}-{arm}-predictions.jsonl"
    binding = {"arm": arm, "split": split, "input_sha256": file_hash(source),
               "registration_sha256": file_hash(ROOT / "registration.json"),
               "adapter_sha256": trained["adapter_sha256"]}
    write_json(path.with_suffix(".binding.json"), binding)
    manifest_path = path.with_suffix(".manifest.json")
    if manifest_path.exists():
        if read_json(manifest_path) != {**binding, "predictions_sha256": file_hash(path), "count": len(rows)}:
            raise ValueError("completed predictions changed")
        return
    # Recover only an incomplete final line; never silently discard an interior corrupt record.
    existing, valid_lines = [], []
    if path.exists():
        lines = path.read_bytes().splitlines(keepends=True)
        for i, line in enumerate(lines):
            try:
                value = json.loads(line)
            except (ValueError, UnicodeDecodeError):
                if i != len(lines) - 1:
                    raise
                break
            existing.append(value)
            valid_lines.append(line.rstrip(b"\r\n") + b"\n")
        recovered = b"".join(valid_lines)
        if recovered != path.read_bytes():
            path.write_bytes(recovered)
    ids = [row["case_id"] for row in existing]
    if len(set(ids)) != len(ids) or ids != [row["case_id"] for row in rows[:len(ids)]]:
        raise ValueError("prediction resume prefix mismatch")
    if len(existing) < len(rows):
        torch, _ = runtime()
        from peft import PeftModel
        model, tokenizer, _ = load_base(torch)
        model = PeftModel.from_pretrained(model, str(ROOT / "artifacts" / arm / "adapter"))
        model.eval()
        with path.open("ab") as handle:
            for index, row in enumerate(rows[len(existing):], start=len(existing) + 1):
                prompt = tokenizer(row["prompt"], return_tensors="pt", add_special_tokens=False)
                length = int(prompt["input_ids"].shape[-1])
                if length > cfg["inference_max_input_tokens"]:
                    raise ValueError("inference prompt too long")
                with torch.no_grad():
                    generated = model.generate(**{k: v.to(model.device) for k, v in prompt.items()},
                        max_new_tokens=cfg["max_new_tokens"], do_sample=False,
                        pad_token_id=tokenizer.pad_token_id, eos_token_id=tokenizer.eos_token_id)
                tokens = generated[0, length:]
                ended = bool(len(tokens) and int(tokens[-1]) == tokenizer.eos_token_id)
                result = {"case_id": row["case_id"], "raw_output": tokenizer.decode(tokens, skip_special_tokens=True).strip(),
                          "ended_with_eos": ended,
                          "hit_generation_limit": len(tokens) >= cfg["max_new_tokens"] and not ended,
                          "generated_token_count": len(tokens), "prompt_token_count": length}
                handle.write((canonical(result) + "\n").encode())
                handle.flush()
                os.fsync(handle.fileno())
                print(f"{split} {arm}: {index}/{len(rows)}", flush=True)
    if len(read_rows(path)) != len(rows):
        raise ValueError("incomplete predictions")
    write_json(manifest_path, {**binding, "predictions_sha256": file_hash(path), "count": len(rows)})


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("stage", choices=["train", "predict"])
    parser.add_argument("arm", choices=["uniform", "structural"])
    parser.add_argument("--split", choices=["development", "confirmation"], default="development")
    args = parser.parse_args()
    train(args.arm) if args.stage == "train" else predict(args.arm, args.split)