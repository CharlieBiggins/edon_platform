#!/usr/bin/env python3
"""Target-blind deterministic verification and fail-closed model override."""

from __future__ import annotations

import importlib
import sys
from typing import Any

from dev018_common import BASE, canonical


def load_engines():
    sys.path.insert(0, str(BASE))
    try:
        return importlib.import_module("rules_baseline"), importlib.import_module("canonicalize")
    finally:
        sys.path.pop(0)


def differing_paths(left: Any, right: Any, prefix: str = "") -> list[str]:
    if isinstance(left, dict) and isinstance(right, dict):
        result: list[str] = []
        for key in sorted(set(left) | set(right)):
            path = f"{prefix}.{key}" if prefix else key
            if key not in left or key not in right:
                result.append(path)
            else:
                result.extend(differing_paths(left[key], right[key], path))
        return result
    if isinstance(left, list) and isinstance(right, list):
        if left == right:
            return []
        return [prefix]
    return [] if left == right else [prefix]


def decision_map(value: Any, prefix: str = "") -> dict[str, Any]:
    result: dict[str, Any] = {}
    if isinstance(value, dict):
        for key, child in value.items():
            path = f"{prefix}.{key}" if prefix else key
            if key == "decision":
                result[path] = child
            else:
                result.update(decision_map(child, path))
    return result


def verify_predictions(
    verifier_inputs: list[dict[str, Any]],
    model_predictions: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    rules, compiler = load_engines()
    model_by_id = {row["case_id"]: row for row in model_predictions}
    if len(model_by_id) != len(model_predictions):
        raise ValueError("duplicate model prediction case identifiers")
    verified: list[dict[str, Any]] = []
    audits: list[dict[str, Any]] = []
    for item in verifier_inputs:
        case_id = item["case_id"]
        model = model_by_id.get(case_id)
        if model is None:
            raise ValueError(f"missing model prediction: {case_id}")
        task_type = item["task_type"]
        compiler_input = item["compiler_input"]
        executor_parsed = rules.predict_input(compiler_input)
        executor_compiled = compiler.compile_prediction(task_type, compiler_input, executor_parsed)
        differences = differing_paths(model.get("compiled"), executor_compiled)
        accepted = (
            model.get("raw_schema_valid") is True
            and model.get("ended_with_eos") is True
            and model.get("hit_generation_limit") is False
            and not differences
        )
        action = "ACCEPT_MODEL" if accepted else "OVERRIDE_WITH_EXECUTOR"
        model_decisions = decision_map(model.get("compiled"))
        executor_decisions = decision_map(executor_compiled)
        unsafe_paths = sorted(
            path for path, value in model_decisions.items()
            if value == "ALLOW" and executor_decisions.get(path) not in {None, "ALLOW"}
        )
        if accepted:
            final = dict(model)
        else:
            final = {
                "case_id": case_id,
                "task_type": task_type,
                "raw_output": canonical(executor_parsed),
                "parsed": executor_parsed,
                "raw_schema_valid": compiler.valid_raw(task_type, executor_parsed),
                "compiled": executor_compiled,
                "compiled_output": canonical(executor_compiled),
                "prompt_token_count": model.get("prompt_token_count"),
                "generated_token_count": model.get("generated_token_count"),
                "generation_token_limit": model.get("generation_token_limit"),
                "ended_with_eos": True,
                "hit_generation_limit": False,
                "confidence": 1.0,
            }
        final.update({
            "verifier_action": action,
            "model_output_accepted": accepted,
            "safety_override": bool(unsafe_paths),
            "binding_authority": False,
        })
        verified.append(final)
        audits.append({
            "case_id": case_id,
            "task_type": task_type,
            "action": action,
            "model_raw_schema_valid": model.get("raw_schema_valid") is True,
            "model_ended_with_eos": model.get("ended_with_eos") is True,
            "model_hit_generation_limit": model.get("hit_generation_limit") is True,
            "compiled_outputs_identical": not differences,
            "differing_paths": differences,
            "unsafe_model_allow_paths": unsafe_paths,
            "safety_override": bool(unsafe_paths),
            "answer_key_accessed": False,
            "binding_authority": False,
        })
    return verified, audits