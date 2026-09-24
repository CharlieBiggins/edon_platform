#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent
CONFIG = ROOT / "configs" / "dev018-verified.json"
EXPERIMENTS = ROOT.parent
ACTIONNET = EXPERIMENTS / "ACTIONNET-DATA-QUAL-018"
BASE = EXPERIMENTS / "CEREBRUM-DEV-009"
MODEL_PARENT = EXPERIMENTS / "CEREBRUM-DEV-017-CAUSAL"


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(canonical(row) + "\n" for row in rows), encoding="utf-8")


def sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return "sha256:" + digest.hexdigest()


def sha256_tree(path: Path) -> str:
    digest = hashlib.sha256()
    for item in sorted(candidate for candidate in path.rglob("*") if candidate.is_file()):
        digest.update(item.relative_to(path).as_posix().encode("utf-8"))
        digest.update(b"\0")
        digest.update(item.read_bytes())
        digest.update(b"\0")
    return "sha256:" + digest.hexdigest()


def model_adapter(config: dict[str, Any]) -> Path:
    return (
        MODEL_PARENT
        / "artifacts"
        / "dev017-parent-dev015-step12-seed-26090642"
        / f"checkpoint-{config['model_parent_step']}"
    )


def summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "records": len(rows),
        "case_ids": len({row["case_id"] for row in rows}),
        "pair_ids": len({row["counterfactual_pair_id"] for row in rows}),
        "task_counts": dict(sorted(Counter(row["task_type"] for row in rows).items())),
        "profile_counts": dict(sorted(Counter(row["generator_profile"] for row in rows).items())),
        "renderer_counts": dict(sorted(Counter(row["selected_renderer"] for row in rows).items())),
        "source_counts": dict(sorted(Counter(row.get("replay_source_protocol", "FRESH") for row in rows).items())),
    }