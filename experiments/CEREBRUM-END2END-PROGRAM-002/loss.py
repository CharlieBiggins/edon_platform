"""Pure token alignment logic, testable without torch or model downloads."""


def structural_spans(text):
    spans, start = [], 0
    for line in text.splitlines(keepends=True):
        if line.startswith(("STEP ", "ACTIONNET_TEMPORAL_PROGRAM_V1", "END_ACTIONNET_TEMPORAL_PROGRAM")):
            spans.append((start, start + len(line)))
        for prefix in ("CLAIM_STATE ", "CLAIM_CERTIFICATE "):
            if line.startswith(prefix):
                spans.append((start, start + len(prefix)))
        start += len(line)
    return spans


def token_weights(text, offsets, multiplier):
    spans = structural_spans(text)
    return [float(multiplier) if any(a < right and b > left for left, right in spans)
            else 1.0 for a, b in offsets]


def encode_row(row, tokenizer, cfg, arm):
    if arm not in cfg["arms"]:
        raise ValueError("unregistered arm")
    prompt = tokenizer(row["prompt"], add_special_tokens=False)["input_ids"]
    target = tokenizer(row["completion"], add_special_tokens=False, return_offsets_mapping=True)
    if tokenizer.eos_token_id is None:
        raise ValueError("EOS token required")
    completion = target["input_ids"] + [tokenizer.eos_token_id]
    multiplier = cfg["structural_weight"] if arm == "structural" else 1.0
    weights = token_weights(row["completion"], target["offset_mapping"], multiplier) + [multiplier]
    if len(prompt) > cfg["inference_max_input_tokens"] or len(prompt) + len(completion) > cfg["max_length"]:
        raise ValueError(f"zero-truncation violation: {row['case_id']}")
    if len(completion) + cfg["generation_token_margin"] > cfg["max_new_tokens"]:
        raise ValueError(f"generation budget smaller than target: {row['case_id']}")
    return {"input_ids": prompt + completion,
            "attention_mask": [1] * (len(prompt) + len(completion)),
            "labels": [-100] * len(prompt) + completion,
            "token_weights": [0.0] * len(prompt) + weights}