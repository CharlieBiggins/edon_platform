"""Tokenizer-qualified complete-pair planning for matched non-padding token budgets."""
from __future__ import annotations

from collections import Counter, defaultdict
from pathlib import Path

from foundation import (ARMS, file_hash, object_hash, read, require, rows,
                        snapshot_hashes, validate_study, write_json, write_rows)


def encode_example(example, tokenizer, config):
    prompt = tokenizer(example["prompt"], add_special_tokens=False)["input_ids"]
    target = tokenizer(example["target"], add_special_tokens=False)["input_ids"]
    require(tokenizer.eos_token_id is not None, "Tokenizer must define EOS")
    completion = target + [tokenizer.eos_token_id]
    require(len(prompt) <= config["max_input_tokens"], "Input token limit exceeded: " + example["example_id"])
    require(len(prompt) + len(completion) <= config["max_length"],
            "Training sequence token limit exceeded: " + example["example_id"])
    require(len(completion) + config["generation_token_margin"] <= config["max_new_tokens"],
            "Target generation limit exceeded: " + example["example_id"])
    return {"nonpadding_tokens": len(prompt) + len(completion),
            "supervised_tokens": len(completion), "prompt_tokens": len(prompt)}


def select_complete_groups(examples, token_counts, budget):
    groups = defaultdict(list)
    for example in examples:
        groups[example["group_id"]].append(example)
    group_ids = sorted(groups)
    require(group_ids and all(len(values) > 0 for values in groups.values()), "Empty training group")
    group_tokens = {group: sum(token_counts[value["example_id"]]["nonpadding_tokens"]
                               for value in groups[group]) for group in group_ids}
    first_pass = sum(group_tokens.values())
    require(first_pass <= budget, "Token budget cannot cover every pair group once")
    plan, total, supervised, cycle = [], 0, 0, 0
    while True:
        advanced = False
        for group in group_ids:
            needed = group_tokens[group]
            if total + needed > budget:
                return plan, {"realized_nonpadding_tokens": total,
                    "realized_supervised_tokens": supervised, "full_pass_tokens": first_pass,
                    "complete_cycles": cycle, "stopped_before_group": group,
                    "unused_budget_tokens": budget - total, "unique_groups": len(group_ids)}
            for example in groups[group]:
                count = token_counts[example["example_id"]]
                plan.append({"sequence": len(plan), "example_id": example["example_id"],
                    "group_id": group, "target_kind": example["target_kind"],
                    "nonpadding_tokens": count["nonpadding_tokens"],
                    "supervised_tokens": count["supervised_tokens"]})
                total += count["nonpadding_tokens"]
                supervised += count["supervised_tokens"]
            advanced = True
        require(advanced, "Token planner made no progress")
        cycle += 1


def make_plans(arm_examples, tokenizer, config, study):
    validate_study(study, config, "draft")
    budget = study["training_budget"]["processed_nonpadding_tokens_per_arm"]
    tolerance = study["training_budget"]["maximum_realized_arm_difference_tokens"]
    require(type(budget) is int and budget > 0, "Set processed token budget before token planning")
    require(type(tolerance) is int and tolerance >= 0, "Set token difference tolerance before token planning")
    plans, audit = {}, {"arms": {}, "requested_tokens_per_arm": budget,
                        "maximum_realized_arm_difference_tokens": tolerance}
    for arm in ARMS:
        values = arm_examples[arm]
        counts = {value["example_id"]: encode_example(value, tokenizer, config) for value in values}
        require(len(counts) == len(values), "Duplicate example identifiers")
        plans[arm], summary = select_complete_groups(values, counts, budget)
        selected = Counter(value["target_kind"] for value in plans[arm])
        summary.update(plan_records=len(plans[arm]), source_examples=len(values),
                       selected_task_counts=dict(selected),
                       maximum_sequence_tokens=max(value["nonpadding_tokens"] for value in counts.values()),
                       maximum_supervised_tokens=max(value["supervised_tokens"] for value in counts.values()))
        audit["arms"][arm] = summary
    difference = abs(audit["arms"]["ordinary"]["realized_nonpadding_tokens"]
                     - audit["arms"]["actionnet"]["realized_nonpadding_tokens"])
    audit["realized_arm_difference_tokens"] = difference
    require(difference <= tolerance, "Realized arm token difference exceeds approved tolerance")
    audit["token_budget_matched"] = True
    audit["step_matching_claimed"] = False
    audit["flop_matching_claimed"] = False
    return plans, audit


def materialize(run_dir, base_snapshot, config, study):
    run_dir, base_snapshot = Path(run_dir), Path(base_snapshot)
    require(not (run_dir / "registration.json").exists(), "Token planning is closed after registration")
    for arm in ARMS:
        require(not (run_dir / "prepared" / ("plan-" + arm + ".jsonl")).exists(),
                "Token plan already exists")
    hashes = snapshot_hashes(base_snapshot)
    base = study["base_snapshot"]
    require(hashes["weights_tree_sha256"] == base["weights_tree_sha256"]
            and hashes["tokenizer_tree_sha256"] == base["tokenizer_tree_sha256"],
            "Base snapshot differs from study commitment")
    from transformers import AutoTokenizer
    tokenizer = AutoTokenizer.from_pretrained(str(base_snapshot), local_files_only=True, use_fast=True)
    require(tokenizer.is_fast, "Registered fast tokenizer required")
    if tokenizer.pad_token_id is None:
        tokenizer.pad_token = tokenizer.eos_token
    tokenizer.padding_side = "right"
    examples = {arm: rows(run_dir / "prepared" / ("train-" + arm + ".jsonl"), "example_id") for arm in ARMS}
    plans, audit = make_plans(examples, tokenizer, config, study)
    audit.update(protocol_id=config["protocol_id"], tokenizer_class=type(tokenizer).__name__,
                 tokenizer_vocab_size=len(tokenizer), snapshot_hashes=hashes,
                 study_sha256=file_hash(run_dir / "study.json"),
                 dataset_hashes={arm: file_hash(run_dir / "prepared" / ("train-" + arm + ".jsonl")) for arm in ARMS})
    for arm in ARMS:
        write_rows(run_dir / "prepared" / ("plan-" + arm + ".jsonl"), plans[arm])
    write_json(run_dir / "prepared/token-audit.json", audit)
    return audit


def verify_plans(run_dir, config, study):
    run_dir = Path(run_dir)
    audit = read(run_dir / "prepared/token-audit.json")
    require(audit["protocol_id"] == config["protocol_id"]
            and audit["study_sha256"] == file_hash(run_dir / "study.json"), "Token audit binding differs")
    require(audit["dataset_hashes"] == {arm: file_hash(run_dir / "prepared" / ("train-" + arm + ".jsonl"))
                                         for arm in ARMS}, "Token audit dataset binding differs")
    difference = abs(audit["arms"]["ordinary"]["realized_nonpadding_tokens"]
                     - audit["arms"]["actionnet"]["realized_nonpadding_tokens"])
    require(audit["token_budget_matched"] is True
            and difference == audit["realized_arm_difference_tokens"]
            and difference <= study["training_budget"]["maximum_realized_arm_difference_tokens"],
            "Token match no longer qualifies")
    for arm in ARMS:
        plan = rows(run_dir / "prepared" / ("plan-" + arm + ".jsonl"))
        require(len(plan) == audit["arms"][arm]["plan_records"], "Token plan count differs")
        require(sum(value["nonpadding_tokens"] for value in plan)
                == audit["arms"][arm]["realized_nonpadding_tokens"], "Token plan total differs")
        groups = Counter(value["group_id"] for value in plan)
        source = rows(run_dir / "prepared" / ("train-" + arm + ".jsonl"), "example_id")
        expected_per_group = Counter(value["group_id"] for value in source)
        require(all(groups[group] % count == 0 for group, count in expected_per_group.items()),
                "Plan contains a partial pair group")
    return audit