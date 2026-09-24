#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent
EDON_ROOT = ROOT.parents[1]
sys.path.insert(0, str(EDON_ROOT / "src"))

from edon.evaluation.closed_loop_dev import ClosedLoopEnvironment


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def main() -> int:
    episodes = read_jsonl(ROOT / "dataset" / "validation-episodes.jsonl")
    oracles = {row["episode_id"]: row for row in read_jsonl(ROOT / "oracle" / "validation-oracle.jsonl")}
    summaries = []
    for episode in episodes:
        run = ClosedLoopEnvironment(episode, oracles[episode["episode_id"]]).run_reference()
        summaries.append({key: value for key, value in run.items() if key != "turns"})
    report = {
        "schema_version": "cerebrum-closed-loop-reference-evaluation.v1",
        "protocol_id": "CEREBRUM-CLOSED-LOOP-DEV-001",
        "status": "PASS" if all(row["episode_success"] for row in summaries) else "FAIL",
        "episode_count": len(summaries),
        "episodes_passed": sum(row["episode_success"] for row in summaries),
        "kernel_rejections": sum(row["kernel_rejections"] for row in summaries),
        "unsafe_proposals": sum(row["unsafe_proposals"] for row in summaries),
        "binding_authority": False,
        "claim_boundary": "Deterministic reference solvability of the development environment only.",
    }
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())