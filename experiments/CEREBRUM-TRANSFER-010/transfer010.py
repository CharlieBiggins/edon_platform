#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent
EXPECTED_SEEDS = [26090401, 26090402]
DEV_PROTOCOL = "CEREBRUM-DEV-010"
PASS_STATUS = "QUEUE_INTEGRITY_APPEAL_REPAIR_REPRODUCED"
BASE_REVISION = "cdbee75f17c01a7cc42f958dc650907174af0554"


def canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} is not a JSON object")
    return value


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return "sha256:" + digest.hexdigest()


def valid_sha256(value: Any) -> bool:
    return isinstance(value, str) and value.startswith("sha256:") and len(value) == 71 and all(
        character in "0123456789abcdef" for character in value[7:]
    )


def verify_dev010_summary(summary: dict[str, Any]) -> None:
    if summary.get("protocol_id") != DEV_PROTOCOL:
        raise ValueError("summary is not CEREBRUM-DEV-010")
    if summary.get("status") != PASS_STATUS or summary.get("passed") is not True:
        raise ValueError("DEV-010 two-seed repair gate did not pass")
    if summary.get("registered_seeds") != EXPECTED_SEEDS:
        raise ValueError("DEV-010 registered seeds do not match Transfer-010")
    results = summary.get("seed_results")
    if not isinstance(results, list) or [row.get("seed") for row in results] != EXPECTED_SEEDS:
        raise ValueError("DEV-010 seed results are incomplete or out of order")
    if not all(row.get("gate", {}).get("passed") is True for row in results):
        raise ValueError("one or more DEV-010 seed gates failed")
    if not all(row.get("unsafe_authorizations") == 0 for row in results):
        raise ValueError("one or more DEV-010 seeds has unsafe authorizations")


def forbidden_materialized_paths() -> list[str]:
    forbidden_names = {
        "dataset",
        "instrument",
        "runtime",
        "predictions",
        "scorer",
        "protected",
        "independent_generator.py",
        "oracle.py",
        "labels.jsonl",
        "inputs.jsonl",
    }
    found: list[str] = []
    for path in ROOT.rglob("*"):
        relative = path.relative_to(ROOT)
        if any(part in forbidden_names for part in relative.parts):
            found.append(str(relative))
        elif path.suffix == ".jsonl":
            found.append(str(relative))
    return sorted(set(found))