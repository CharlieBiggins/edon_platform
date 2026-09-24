#!/usr/bin/env python3
"""Hash-freeze all four Qwen prediction files before protected scoring."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent
SEEDS = (26082341, 26082342)


def digest(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    records = []
    for condition in ("control", "platform002"):
        for seed in SEEDS:
            path = ROOT / "predictions" / f"qwen-{condition}-seed-{seed}.jsonl"
            if not path.is_file():
                raise SystemExit(f"missing prediction file: {path.name}")
            count = sum(1 for line in path.read_text().splitlines() if line)
            if count != 320:
                raise SystemExit(f"prediction file must contain 320 rows: {path.name}")
            records.append({
                "condition": condition, "seed": seed,
                "path": str(path.relative_to(ROOT)), "sha256": digest(path), "rows": count,
            })
    freeze = {
        "schema_version": "cerebrum-platform-contrib-qwen-freeze.v1",
        "experiment_id": "CEREBRUM-PLATFORM-CONTRIB-001",
        "predictions": records,
        "labels_opened": False,
        "complete": True,
        "binding_authority": False,
    }
    (ROOT / "results" / "qwen_prediction_freeze.json").write_text(
        json.dumps(freeze, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(freeze, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())