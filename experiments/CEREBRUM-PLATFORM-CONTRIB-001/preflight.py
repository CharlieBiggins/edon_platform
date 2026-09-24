#!/usr/bin/env python3
"""Preflight the frozen Qwen contribution experiment without training."""

from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent
REQUIRED_MODULES = ("torch", "transformers", "datasets", "peft", "bitsandbytes")


def load_jsonl(path: Path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def main() -> int:
    training_manifest = json.loads((ROOT / "training" / "manifest.json").read_text())
    protected_manifest = json.loads((ROOT / "protected" / "manifest.json").read_text())
    control = load_jsonl(ROOT / "training" / "control.jsonl")
    active = load_jsonl(ROOT / "training" / "platform002.jsonl")
    protected = load_jsonl(ROOT / "protected" / "public_inputs.jsonl")
    train_prompts = {
        hashlib.sha256(row["observation"]["prompt"].encode()).hexdigest()
        for row in control + active
    }
    protected_prompts = {
        hashlib.sha256(row["observation"]["prompt"].encode()).hexdigest()
        for row in protected
    }
    modules = {name: importlib.util.find_spec(name) is not None for name in REQUIRED_MODULES}
    cuda = False
    if modules["torch"]:
        import torch
        cuda = bool(torch.cuda.is_available())
    checks = {
        "matched_training_counts": len(control) == len(active) == 800,
        "training_manifest_matched": training_manifest["matched_record_count"] is True,
        "protected_case_count": len(protected) == protected_manifest["case_count"] == 320,
        "protected_generator_separate": protected_manifest["imports_actionnet_or_training_code"] is False,
        "zero_prompt_overlap": not (train_prompts & protected_prompts),
        "fresh_qwen_target_custody": False,
        "qwen_runtime_dependencies": all(modules.values()),
        "cuda_available": cuda,
    }
    ready = all(checks.values())
    result = {
        "schema_version": "cerebrum-platform-contrib-preflight.v1",
        "experiment_id": "CEREBRUM-PLATFORM-CONTRIB-001",
        "status": "READY_FOR_CONFIRMATORY_QWEN_EXECUTION" if ready else "BLOCKED_MISSING_QWEN_GPU_AND_FRESH_TARGET_CUSTODY",
        "checks": checks,
        "runtime_modules": modules,
        "binding_authority": False,
        "actual_cerebrum_result_exists": False,
        "current_target_confirmatory_eligible": False,
    }
    (ROOT / "results" / "preflight.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if ready else 2


if __name__ == "__main__":
    raise SystemExit(main())