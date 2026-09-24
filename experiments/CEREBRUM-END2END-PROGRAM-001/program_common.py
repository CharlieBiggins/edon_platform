#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent
EXPERIMENTS = ROOT.parent
ACTIONNET = EXPERIMENTS / "ACTIONNET-DATA-QUAL-021-PROGRAM"
DEV020 = EXPERIMENTS / "CEREBRUM-DEV-020-INTERFACE-CALIBRATION"
CONFIG = ROOT / "configs" / "program-001.json"
PROGRAM_IR_PATH = ACTIONNET / "program_ir.py"


def _load_program_ir():
    spec = importlib.util.spec_from_file_location("actionnet_program_ir_for_cerebrum", PROGRAM_IR_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load program interpreter: {PROGRAM_IR_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


IR = _load_program_ir()


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


def artifact_root(config: dict[str, Any]) -> Path:
    return ROOT / "artifacts" / config["training_run_id"]


def candidate_specs(config: dict[str, Any]) -> list[dict[str, Any]]:
    root = artifact_root(config)
    return [
        {
            "candidate_id": candidate["candidate_id"],
            "step": int(candidate["step"]),
            "adapter": root / f"checkpoint-{int(candidate['step'])}",
        }
        for candidate in config["development_candidates"]
    ]