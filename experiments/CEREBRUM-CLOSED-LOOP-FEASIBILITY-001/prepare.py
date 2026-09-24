"""Select a deterministic 12-episode feasibility subset without mutating the predecessor."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import random

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT.parent / "CEREBRUM-CLOSED-LOOP-DEV-001"


def load_source():
    spec = importlib.util.spec_from_file_location("closed_loop_source_generate", SOURCE / "generate.py")
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module


def select():
    source = load_source(); design = json.loads((SOURCE / "config/design.json").read_text(encoding="utf-8"))
    rng = random.Random(design["generator_seed"])
    source.generate_split(split="TRAIN", counts=design["split_design"]["train_pair_classes"],
        profiles=design["training_profiles"], renderers=design["training_renderers"],
        scenarios=design["scenario_families"], rng=rng)
    episodes, oracles = source.generate_split(split="VALIDATION",
        counts=design["split_design"]["validation_pair_classes"],
        profiles=design["heldout_validation_profiles"], renderers=design["heldout_validation_renderers"],
        scenarios=design["scenario_families"], rng=rng)
    oracle = {row["episode_id"]: row for row in oracles}
    unused = list(episodes); selected = []
    def take(kind, predicate, count=3):
        chosen = [row for row in unused if predicate(row, oracle[row["episode_id"]])][:count]
        if len(chosen) != count: raise ValueError("Insufficient episodes for " + kind)
        for row in chosen: unused.remove(row)
        selected.extend((row, oracle[row["episode_id"]], {"episode_id": row["episode_id"],
            "episode_type": kind, "reject_phase": "DISPATCH" if kind == "KERNEL_REJECTION_REVISION" else None,
            "reason": "Registered recoverable resource-policy hold" if kind == "KERNEL_REJECTION_REVISION" else None})
            for row in chosen)
    take("NORMAL_SUCCESS", lambda row, item: not item["requires_replan"])
    take("KERNEL_REJECTION_REVISION", lambda row, item: not item["requires_replan"])
    take("DELAYED_OR_CONFLICTING_EVIDENCE", lambda row, item:
         item["requires_replan"] and any(word in item["primary_failure_reason"].lower() for word in ("stale", "conflict")))
    take("FAILURE_MONITOR_REPLAN", lambda row, item: item["requires_replan"])
    return ([item[0] for item in selected], [item[1] for item in selected], [item[2] for item in selected])