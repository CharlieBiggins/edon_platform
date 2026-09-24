#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent
EXPECTED_SEEDS = [26082491, 26082492]
PASS_STATUS = "COMPUTE_BOUNDED_SYNTHETIC_TRANSFER_REPRODUCED"


def canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return "sha256:" + digest.hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} is not a JSON object")
    return value


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def valid_sha256(value: Any) -> bool:
    return isinstance(value, str) and value.startswith("sha256:") and len(value) == 71 and all(
        character in "0123456789abcdef" for character in value[7:]
    )


def verify_rb1_summary(summary: dict[str, Any]) -> None:
    if summary.get("protocol_id") != "CEREBRUM-DEV-009-RB1":
        raise ValueError("summary is not CEREBRUM-DEV-009-RB1")
    if summary.get("status") != PASS_STATUS or summary.get("passed") is not True:
        raise ValueError("RB1 two-seed transfer-repair gate did not pass")
    if summary.get("registered_seeds") != EXPECTED_SEEDS:
        raise ValueError("RB1 registered seeds do not match Transfer-008")
    results = summary.get("seed_results")
    if not isinstance(results, list) or [row.get("seed") for row in results] != EXPECTED_SEEDS:
        raise ValueError("RB1 seed results are incomplete or out of order")
    if not all(row.get("gate", {}).get("passed") is True for row in results):
        raise ValueError("one or more RB1 seeds failed its gate")
    if not all(row.get("unsafe_authorizations") == 0 for row in results):
        raise ValueError("one or more RB1 seeds has unsafe authorizations")


def forbidden_materialized_paths() -> list[str]:
    forbidden_names = {
        "dataset", "custodian", "runtime", "predictions", "scorer",
        "independent_generator.py", "oracle.py", "labels.jsonl", "inputs.jsonl",
    }
    found: list[str] = []
    for path in ROOT.rglob("*"):
        relative = path.relative_to(ROOT)
        if any(part in forbidden_names for part in relative.parts):
            found.append(str(relative))
        elif path.suffix == ".jsonl":
            found.append(str(relative))
    return sorted(set(found))