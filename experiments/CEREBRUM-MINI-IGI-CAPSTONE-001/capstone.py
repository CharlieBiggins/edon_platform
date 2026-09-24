#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent
EDON_ROOT = ROOT.parents[1]
EXPECTED_SEEDS = [26082491, 26082492]
READY_STATUS = "SHELL_READY_PREREQUISITES_UNMET_MATERIALIZATION_UNAUTHORIZED"


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def sha256_path(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def forbidden_materialized_paths() -> list[str]:
    forbidden_parts = {
        "instrument",
        "protected_cases",
        "prompts",
        "labels",
        "generators",
        "oracles",
        "runtime",
        "predictions",
        "scorer",
        "score",
        "materialization_authorization.json",
    }
    forbidden_names = {
        "generator.py",
        "oracle.py",
        "scorer.py",
        "cases.jsonl",
        "inputs.jsonl",
        "labels.jsonl",
        "predictions.jsonl",
    }
    found: list[str] = []
    for path in ROOT.rglob("*"):
        relative = path.relative_to(ROOT)
        if any(part in forbidden_parts for part in relative.parts):
            found.append(str(relative))
        elif path.name in forbidden_names or path.suffix == ".jsonl":
            found.append(str(relative))
    return sorted(set(found))


def all_null(values: list[Any]) -> bool:
    return all(value is None for value in values)
