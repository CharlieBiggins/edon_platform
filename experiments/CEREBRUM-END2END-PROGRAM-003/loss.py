"""Uniform completion-token loss for BOTH arms; no structural reweighting."""
from trace_ir import completion_for, prompt_for


def completion_loss(logits, labels, chunk_size=128):
    """Per-example causal CE, checkpointed by token chunk to limit CE temporaries."""
    import torch
    import torch.nn.functional as F
    from torch.utils.checkpoint import checkpoint
    losses = []
    for index in range(logits.shape[0]):
        target = labels[index, 1:]
        count = target.ne(-100).sum()
        if not int(count):
            raise ValueError("example has no supervised completion tokens")
        total = logits[index, 0, 0] * 0
        for start in range(0, len(target), chunk_size):
            stop = min(start + chunk_size, len(target))
            if not bool(target[start:stop].ne(-100).any()):
                continue
            def block(x, y):
                return F.cross_entropy(x.float(), y, ignore_index=-100, reduction="sum")
            x, y = logits[index, start:stop], target[start:stop]
            total = total + (checkpoint(block, x, y, use_reentrant=False)
                             if torch.is_grad_enabled() and x.requires_grad else block(x, y))
        losses.append(total / count)
    return torch.stack(losses).mean()


def loss_self_test():
    import torch
    import torch.nn.functional as F
    with torch.random.fork_rng(devices=[]):
        torch.manual_seed(3)
        x = torch.randn(2, 7, 11, requires_grad=True)
        y = torch.tensor([[-100, -100, 3, 4, 5, 6, -100], [-100, 1, 2, 3, 4, 5, 6]])
        actual = completion_loss(x, y, 2)
        expected = torch.stack([F.cross_entropy(x[i, :-1], y[i, 1:], ignore_index=-100)
                                for i in range(2)]).mean()
        a = torch.autograd.grad(actual, x, retain_graph=True)[0]
        b = torch.autograd.grad(expected, x)[0]
        if not torch.allclose(actual, expected, atol=1e-6) or not torch.allclose(a, b, atol=1e-6):
            raise ValueError("chunked CE value/gradient mismatch")
    return True


def encode_row(row, tokenizer, cfg, arm):
    prompt = tokenizer(prompt_for(row["prompt"], arm), add_special_tokens=False)["input_ids"]
    target = tokenizer(completion_for(row, arm), add_special_tokens=False)["input_ids"]
    if tokenizer.eos_token_id is None:
        raise ValueError("EOS token required")
    completion = target + [tokenizer.eos_token_id]
    if len(prompt) > cfg["inference_max_input_tokens"] or len(prompt) + len(completion) > cfg["max_length"]:
        raise ValueError("zero-truncation violation: " + row["case_id"])
    if len(completion) + cfg["generation_token_margin"] > cfg["max_new_tokens"]:
        raise ValueError("generation budget smaller than complete target")
    return {"input_ids": prompt + completion, "attention_mask": [1] * (len(prompt) + len(completion)),
            "labels": [-100] * len(prompt) + completion,
            "token_weights": [0.0] * len(prompt) + [1.0] * len(completion)}