"""Paid single-L4 training and native-program prediction; never imported by CPU preflight."""
from __future__ import annotations

import importlib.metadata
import json
import os
from pathlib import Path
import random
import time

from foundation import (ARMS, file_hash, read, require, rows, snapshot_hashes,
                        tree_hash, validate_study, write_bytes, write_json)
from token_budget import encode_example, verify_plans


def write_or_verify(path, value):
    path = Path(path)
    if path.exists():
        require(read(path) == value, "Immutable evidence differs: " + str(path))
    else:
        write_json(path, value)


def runtime_environment(config):
    versions = {name: importlib.metadata.version(name) for name in config["required_packages"]}
    require(versions == config["required_packages"], "Pinned package versions required")
    import torch
    hardware = config["hardware"]
    require(torch.cuda.is_available() and torch.cuda.device_count() == hardware["visible_gpus"]
            and int(os.environ.get("WORLD_SIZE", "1")) == 1, "Exactly one visible CUDA GPU required")
    require(str(torch.__version__) == hardware["torch"] and torch.version.cuda == hardware["cuda"]
            and torch.cuda.get_device_name(0) == hardware["gpu"], "Registered L4 runtime required")
    return torch, versions


def completion_loss(logits, labels, chunk_size):
    import torch
    import torch.nn.functional as functional
    from torch.utils.checkpoint import checkpoint
    losses = []
    for index in range(logits.shape[0]):
        target = labels[index, 1:]
        count = target.ne(-100).sum()
        require(int(count) > 0, "Example has no supervised tokens")
        total = logits[index, 0, 0] * 0
        for start in range(0, len(target), chunk_size):
            stop = min(start + chunk_size, len(target))
            if not bool(target[start:stop].ne(-100).any()):
                continue
            def block(values, expected):
                return functional.cross_entropy(values.float(), expected, ignore_index=-100, reduction="sum")
            values, expected = logits[index, start:stop], target[start:stop]
            total = total + (checkpoint(block, values, expected, use_reentrant=False)
                             if torch.is_grad_enabled() and values.requires_grad else block(values, expected))
        losses.append(total / count)
    return torch.stack(losses).mean()


def loss_self_test(torch, chunk_size):
    import torch.nn.functional as functional
    with torch.random.fork_rng(devices=[]):
        torch.manual_seed(19)
        values = torch.randn(2, 7, 11, requires_grad=True)
        labels = torch.tensor([[-100, -100, 3, 4, 5, 6, -100], [-100, 1, 2, 3, 4, 5, 6]])
        actual = completion_loss(values, labels, chunk_size)
        expected = torch.stack([functional.cross_entropy(values[i, :-1], labels[i, 1:], ignore_index=-100)
                                for i in range(2)]).mean()
        left = torch.autograd.grad(actual, values, retain_graph=True)[0]
        right = torch.autograd.grad(expected, values)[0]
        require(torch.allclose(actual, expected, atol=1e-6)
                and torch.allclose(left, right, atol=1e-6), "Loss value/gradient self-test failed")


def load_tokenizer(base_snapshot):
    from transformers import AutoTokenizer
    tokenizer = AutoTokenizer.from_pretrained(str(base_snapshot), local_files_only=True, use_fast=True)
    require(tokenizer.is_fast and tokenizer.eos_token_id is not None, "Fast tokenizer with EOS required")
    if tokenizer.pad_token_id is None:
        tokenizer.pad_token = tokenizer.eos_token
    tokenizer.padding_side = "right"
    return tokenizer


def load_base(torch, base_snapshot):
    from transformers import AutoModelForCausalLM, BitsAndBytesConfig
    tokenizer = load_tokenizer(base_snapshot)
    dtype = torch.bfloat16 if torch.cuda.is_bf16_supported() else torch.float16
    model = AutoModelForCausalLM.from_pretrained(str(base_snapshot), local_files_only=True,
        dtype=dtype, device_map={"": 0}, quantization_config=BitsAndBytesConfig(
            load_in_4bit=True, bnb_4bit_quant_type="nf4", bnb_4bit_use_double_quant=True,
            bnb_4bit_compute_dtype=dtype))
    return model, tokenizer, dtype


def encode(example, tokenizer, config):
    count = encode_example(example, tokenizer, config)
    prompt = tokenizer(example["prompt"], add_special_tokens=False)["input_ids"]
    target = tokenizer(example["target"], add_special_tokens=False)["input_ids"] + [tokenizer.eos_token_id]
    result = {"input_ids": prompt + target, "attention_mask": [1] * (len(prompt) + len(target)),
              "labels": [-100] * len(prompt) + target, "example_id": example["example_id"]}
    require(len(result["input_ids"]) == count["nonpadding_tokens"]
            and sum(value != -100 for value in result["labels"]) == count["supervised_tokens"],
            "Tokenizer accounting differs")
    return result


def compute_cap_seconds(study):
    budget = study["training_budget"]
    return 3600 * min(budget["maximum_gpu_hours_per_run"],
                      budget["maximum_cost_usd_per_run"] / budget["gpu_hourly_price_usd"])


def estimated_cost(seconds, study):
    return seconds / 3600 * study["training_budget"]["gpu_hourly_price_usd"]


def existing_compute(run_dir):
    seconds, cost = 0.0, 0.0
    runtime_path = Path(run_dir) / "results/runtime-readiness.json"
    if runtime_path.exists():
        value = read(runtime_path); seconds += value.get("gpu_seconds", 0); cost += value.get("estimated_cost_usd", 0)
    for path in Path(run_dir).glob("artifacts/*/training.json"):
        value = read(path); seconds += value["gpu_seconds"]; cost += value["estimated_cost_usd"]
    for path in Path(run_dir).glob("results/screen-*.manifest.json"):
        value = read(path); seconds += value["gpu_seconds"]; cost += value["estimated_cost_usd"]
    return seconds, cost


def available_cap_seconds(run_dir, study):
    seconds, cost = existing_compute(run_dir)
    budget = study["training_budget"]
    remaining_hours = budget["maximum_total_gpu_hours"] - seconds / 3600
    remaining_cost_seconds = ((budget["maximum_total_cost_usd"] - cost)
                              / budget["gpu_hourly_price_usd"] * 3600)
    limit = min(compute_cap_seconds(study), remaining_hours * 3600, remaining_cost_seconds)
    require(limit > 0, "A-stage total compute/cost cap reached")
    return limit


def runtime_preflight(run_dir, base_snapshot, config, study, registration):
    run_dir, base_snapshot = Path(run_dir), Path(base_snapshot)
    validate_study(study, config, "registration")
    output = run_dir / "results/runtime-readiness.json"
    if output.exists():
        value = read(output)
        require(value["registration_sha256"] == file_hash(run_dir / "registration.json"),
                "Runtime readiness binding differs")
        return value
    limit = available_cap_seconds(run_dir, study); started = time.monotonic()
    hashes = snapshot_hashes(base_snapshot)
    require(hashes["weights_tree_sha256"] == study["base_snapshot"]["weights_tree_sha256"]
            and hashes["tokenizer_tree_sha256"] == study["base_snapshot"]["tokenizer_tree_sha256"],
            "Base snapshot differs")
    token_audit = verify_plans(run_dir, config, study)
    torch, versions = runtime_environment(config)
    tokenizer = load_tokenizer(base_snapshot)
    for arm in ARMS:
        examples = {value["example_id"]: value for value in rows(
            run_dir / "prepared" / ("train-" + arm + ".jsonl"), "example_id")}
        for item in rows(run_dir / "prepared" / ("plan-" + arm + ".jsonl")):
            actual = encode_example(examples[item["example_id"]], tokenizer, config)
            require(actual["nonpadding_tokens"] == item["nonpadding_tokens"]
                    and actual["supervised_tokens"] == item["supervised_tokens"],
                    "Runtime tokenizer differs from frozen token plan")
    loss_self_test(torch, config["loss_token_chunk_size"])
    elapsed = time.monotonic() - started
    require(elapsed <= limit, "Runtime preflight exceeded registered cap")
    report = {"protocol_id": config["protocol_id"],
        "registration_sha256": file_hash(run_dir / "registration.json"),
        "source_inventory_sha256": registration["source_inventory_sha256"],
        "study_sha256": file_hash(run_dir / "study.json"), "snapshot_hashes": hashes,
        "token_audit_sha256": file_hash(run_dir / "prepared/token-audit.json"),
        "packages": versions, "torch": str(torch.__version__), "cuda": torch.version.cuda,
        "gpu": torch.cuda.get_device_name(0), "loss_value_and_gradient_passed": True,
        "token_budget_matched": token_audit["token_budget_matched"],
        "paid_execution_approved": True, "binding_authority": False,
        "gpu_seconds": elapsed, "estimated_cost_usd": estimated_cost(elapsed, study),
        "billing_note": "Cost values are registered-price estimates, not provider invoice attestation"}
    write_json(output, report)
    return report


def trained_manifest(run_dir, arm, config):
    require(arm in ARMS, "Unknown arm")
    run_dir = Path(run_dir)
    value = read(run_dir / "artifacts" / arm / "training.json")
    require(value["registration_sha256"] == file_hash(run_dir / "registration.json")
            and value["plan_sha256"] == file_hash(run_dir / "prepared" / ("plan-" + arm + ".jsonl"))
            and value["adapter_sha256"] == tree_hash(run_dir / "artifacts" / arm / "adapter")
            and value["fresh_adapter_from_base"] is True and value["parent_adapter"] is None,
            "Trained adapter evidence differs")
    return value


def train(run_dir, base_snapshot, arm, config, study):
    run_dir, base_snapshot = Path(run_dir), Path(base_snapshot)
    require(arm in ARMS, "Unknown arm")
    validate_study(study, config, "registration")
    ready = read(run_dir / "results/runtime-readiness.json")
    require(ready["registration_sha256"] == file_hash(run_dir / "registration.json"),
            "Runtime readiness binding differs")
    completed = run_dir / "artifacts" / arm / "training.json"
    if completed.exists():
        return trained_manifest(run_dir, arm, config)
    torch, versions = runtime_environment(config)
    from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
    from transformers import Trainer, TrainingArguments, TrainerCallback, set_seed
    from transformers.trainer_utils import get_last_checkpoint
    seed_label = study["training_seed_label"]
    seed = config["seed_pairs"][seed_label]
    set_seed(seed); random.seed(seed)
    binding = {"protocol_id": config["protocol_id"], "arm": arm,
        "registration_sha256": file_hash(run_dir / "registration.json"),
        "plan_sha256": file_hash(run_dir / "prepared" / ("plan-" + arm + ".jsonl")),
        "runtime_readiness_sha256": file_hash(run_dir / "results/runtime-readiness.json"),
        "base_weights_tree_sha256": study["base_snapshot"]["weights_tree_sha256"],
        "tokenizer_tree_sha256": study["base_snapshot"]["tokenizer_tree_sha256"],
        "seed": seed, "packages": versions}
    start_path = run_dir / "artifacts" / arm / "start.json"
    previously_started = start_path.exists()
    write_or_verify(start_path, binding)
    checkpoints = run_dir / "artifacts" / arm / "checkpoints"
    last = get_last_checkpoint(str(checkpoints)) if checkpoints.exists() else None
    require(not previously_started or last is not None,
            "Previous start has no resumable checkpoint; audit before restart")
    examples = {value["example_id"]: value for value in rows(
        run_dir / "prepared" / ("train-" + arm + ".jsonl"), "example_id")}
    plan = rows(run_dir / "prepared" / ("plan-" + arm + ".jsonl"))
    model, tokenizer, dtype = load_base(torch, base_snapshot)
    encoded = [encode(examples[item["example_id"]], tokenizer, config) for item in plan]
    require(sum(len(value["input_ids"]) for value in encoded)
            == read(run_dir / "prepared/token-audit.json")["arms"][arm]["realized_nonpadding_tokens"],
            "Encoded training token total differs")
    model = prepare_model_for_kbit_training(model, use_gradient_checkpointing=True)
    lora = config["lora"]
    model = get_peft_model(model, LoraConfig(r=lora["r"], lora_alpha=lora["alpha"],
        lora_dropout=lora["dropout"], target_modules=lora["target_modules"], bias="none", task_type="CAUSAL_LM"))
    model.config.use_cache = False

    def collate(features):
        width = max(len(value["input_ids"]) for value in features)
        result = {}
        for key, pad in (("input_ids", tokenizer.pad_token_id), ("attention_mask", 0), ("labels", -100)):
            result[key] = torch.tensor([value[key] + [pad] * (width - len(value[key])) for value in features],
                                       dtype=torch.long)
        return result

    class CompletionTrainer(Trainer):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs); self.model_accepts_loss_kwargs = False
        def compute_loss(self, model, inputs, return_outputs=False, num_items_in_batch=None):
            labels = inputs.pop("labels"); output = model(**inputs)
            value = completion_loss(output.logits, labels, config["loss_token_chunk_size"])
            return (value, output) if return_outputs else value

    limit = available_cap_seconds(run_dir, study)
    started = time.monotonic()
    class StopBudget(TrainerCallback):
        def on_step_end(self, args, state, control, **kwargs):
            if time.monotonic() - started > limit:
                raise RuntimeError("Registered per-run GPU/cost cap reached; checkpoint is preserved")
            return control

    arguments = TrainingArguments(output_dir=str(checkpoints), max_steps=len(encoded), num_train_epochs=1,
        per_device_train_batch_size=1, gradient_accumulation_steps=1,
        learning_rate=config["learning_rate"], lr_scheduler_type="constant", warmup_steps=0,
        weight_decay=config["weight_decay"], save_steps=config["checkpoint_every_steps"], save_total_limit=2,
        logging_steps=4, bf16=dtype == torch.bfloat16, fp16=dtype == torch.float16,
        gradient_checkpointing=True, gradient_checkpointing_kwargs={"use_reentrant": False},
        report_to=[], remove_unused_columns=False, optim="paged_adamw_8bit", seed=seed, data_seed=seed,
        dataloader_drop_last=False)
    trainer = CompletionTrainer(model=model, args=arguments, train_dataset=encoded,
                                data_collator=collate, callbacks=[StopBudget()])
    result = trainer.train(resume_from_checkpoint=last)
    elapsed = time.monotonic() - started
    require(trainer.state.global_step == len(encoded), "Training did not reach the frozen token plan")
    adapter = run_dir / "artifacts" / arm / "adapter"
    trainer.save_model(str(adapter)); tokenizer.save_pretrained(str(adapter))
    manifest = {**binding, "step": trainer.state.global_step, "plan_records": len(encoded),
        "processed_nonpadding_tokens": sum(len(value["input_ids"]) for value in encoded),
        "supervised_tokens": sum(sum(token != -100 for token in value["labels"]) for value in encoded),
        "adapter_sha256": tree_hash(adapter), "fresh_adapter_from_base": True, "parent_adapter": None,
        "metrics": result.metrics, "resumed": last is not None, "gpu_seconds": elapsed,
        "estimated_cost_usd": estimated_cost(elapsed, study), "gpu": torch.cuda.get_device_name(0),
        "dtype": str(dtype), "billing_attested": False, "transfer_authorized": False, "binding_authority": False}
    write_json(completed, manifest)
    return manifest


def _read_prefix(path, expected_ids):
    if not path.exists():
        return [], b""
    records, kept = [], []
    parts = path.read_bytes().splitlines(keepends=True)
    for index, line in enumerate(parts):
        try:
            value = json.loads(line)
        except (ValueError, UnicodeDecodeError):
            require(index == len(parts) - 1, "Corrupt interior prediction")
            break
        records.append(value); kept.append(line.rstrip(b"\r\n") + b"\n")
    ids = [value["case_id"] for value in records]
    require(ids == expected_ids[:len(ids)] and len(ids) == len(set(ids)), "Prediction prefix differs")
    return records, b"".join(kept)


def predict(run_dir, base_snapshot, arm, config, study):
    run_dir, base_snapshot = Path(run_dir), Path(base_snapshot)
    validate_study(study, config, "registration")
    trained = trained_manifest(run_dir, arm, config)
    inputs = rows(run_dir / "prepared/screen-inputs.jsonl", "case_id")
    path = run_dir / "results" / ("screen-" + arm + "-predictions.jsonl")
    binding = {"protocol_id": config["protocol_id"], "arm": arm,
        "registration_sha256": file_hash(run_dir / "registration.json"),
        "input_sha256": file_hash(run_dir / "prepared/screen-inputs.jsonl"),
        "adapter_sha256": trained["adapter_sha256"],
        "runtime_readiness_sha256": file_hash(run_dir / "results/runtime-readiness.json"),
        "shared_output_format": config["shared_output_format"]}
    write_or_verify(path.with_suffix(".binding.json"), binding)
    manifest_path = path.with_suffix(".manifest.json")
    if manifest_path.exists():
        value = read(manifest_path)
        require(value["binding"] == binding and value["count"] == config["screen_records"]
                and value["predictions_sha256"] == file_hash(path), "Prediction manifest differs")
        return value
    records, valid = _read_prefix(path, [value["case_id"] for value in inputs])
    if path.exists() and valid != path.read_bytes():
        write_bytes(path.with_suffix(".interrupted-" + file_hash(path).split(":")[1]), path.read_bytes())
        path.write_bytes(valid)
    torch, _ = runtime_environment(config)
    from peft import PeftModel
    base, tokenizer, _ = load_base(torch, base_snapshot)
    model = PeftModel.from_pretrained(base, str(run_dir / "artifacts" / arm / "adapter"))
    model.eval()
    limit = available_cap_seconds(run_dir, study)
    started = time.monotonic()
    with path.open("ab") as stream:
        for index, value in enumerate(inputs[len(records):], start=len(records) + 1):
            require(time.monotonic() - started <= limit, "Prediction GPU/cost cap reached; prefix preserved")
            encoded = tokenizer(value["prompt"], return_tensors="pt", add_special_tokens=False)
            length = int(encoded["input_ids"].shape[-1])
            require(length <= config["max_input_tokens"], "Screen prompt too long")
            one = time.monotonic()
            with torch.no_grad():
                output = model.generate(**{key: item.to(model.device) for key, item in encoded.items()},
                    max_new_tokens=config["max_new_tokens"], do_sample=False,
                    pad_token_id=tokenizer.pad_token_id, eos_token_id=tokenizer.eos_token_id)
            tokens = output[0, length:]
            ended = bool(len(tokens) and int(tokens[-1]) == tokenizer.eos_token_id)
            record = {"case_id": value["case_id"],
                "raw_output": tokenizer.decode(tokens, skip_special_tokens=True).strip(),
                "ended_with_eos": ended,
                "hit_generation_limit": len(tokens) >= config["max_new_tokens"] and not ended,
                "prompt_token_count": length, "generated_token_count": len(tokens),
                "generation_seconds": time.monotonic() - one}
            stream.write((json.dumps(record, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n").encode())
            stream.flush(); os.fsync(stream.fileno())
            print(f"screen {arm}: {index}/{len(inputs)}", flush=True)
    elapsed = time.monotonic() - started
    require(len(rows(path, "case_id")) == config["screen_records"], "Incomplete prediction screen")
    manifest = {"binding": binding, "count": config["screen_records"], "predictions_sha256": file_hash(path),
        "gpu_seconds": elapsed, "estimated_cost_usd": estimated_cost(elapsed, study),
        "billing_attested": False}
    write_json(manifest_path, manifest)
    return manifest