#!/usr/bin/env python3
"""Additive observability repair for ACTIONNET-DATA-QUAL-001.

The predecessor is loaded as source history and patched only at its public
rendering boundary. The original result package is never overwritten.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent
PREDECESSOR = ROOT.parent / "ACTIONNET-DATA-QUAL-001" / "actionnet.py"
SPEC = importlib.util.spec_from_file_location("actionnet_data_qual_001_source", PREDECESSOR)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("cannot load ACTIONNET-DATA-QUAL-001 source")
base = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(base)


def public_state(state: dict[str, Any]) -> dict[str, Any]:
    visible = {key: value for key, value in state.items() if key != "malformed"}
    if state.get("malformed"):
        # Expose a malformed typed field rather than an answer label.
        visible["actor_rank"] = "malformed-rank"
    return visible


def render(style: str, domain: str, state: dict[str, Any], events: list[dict[str, Any]]) -> tuple[str, str]:
    visible = public_state(state)
    if style == "FORMAL":
        content = json.dumps({"domain": domain, "state": visible, "events": events}, sort_keys=True, separators=(",", ":"))
        return "application/json", content
    if style == "EVENT_LOG":
        event_text = "; ".join(f"{event['type']}={json.dumps(event.get('value'), separators=(',', ':'))}" for event in events)
        content = (
            f"domain={domain}\nactor={visible['actor_id']} rank={visible['actor_rank']} required={visible['required_rank']}\n"
            f"evidence={visible['evidence']} time={visible['query_time']} window={visible['valid_from']}..{visible['valid_to']}\n"
            f"capacity={visible['capacity']} demand={visible['demand']}\nevents={event_text}"
        )
        return "text/plain;profile=event-log", content
    if style == "MEMO":
        event_text = ", then ".join(
            f"{event['type'].lower().replace('_', ' ')}={json.dumps(event.get('value'), separators=(',', ':'))}"
            for event in events
        )
        content = (
            f"In the {domain} institution, actor {visible['actor_id']} holds rank {visible['actor_rank']} where rank "
            f"{visible['required_rank']} is required. Evidence is {str(visible['evidence']).lower()}, the effective interval is "
            f"{visible['valid_from']} through {visible['valid_to']}, current time is {visible['query_time']}, and resource demand "
            f"is {visible['demand']} against capacity {visible['capacity']}. The recorded event sequence is {event_text}. "
            "Return a typed institutional certificate."
        )
        return "text/plain;profile=memo", content
    raise ValueError(style)


base.public_state = public_state
base.render = render

DECISIONS = base.DECISIONS
INTERVENTIONS = base.INTERVENTIONS
SEMANTIC_STATES = base.SEMANTIC_STATES
canonical = base.canonical
digest = base.digest
split_disjoint = base.split_disjoint


def sanitize_for_training(generated: dict[str, Any]) -> dict[str, Any]:
    """Move audit identifiers outside the model-facing input object."""
    for split, rows in generated["datasets"].items():
        repaired: list[dict[str, Any]] = []
        for row in rows:
            original_input = dict(row["input"])
            case_id = original_input.pop("case_id")
            institution_lineage = original_input.pop("institution_lineage")
            if split == "public_holdout":
                repaired.append({"case_id": case_id, "input": original_input})
            else:
                metadata = dict(row["metadata"])
                metadata["institution_lineage"] = institution_lineage
                repaired.append({"case_id": case_id, "input": original_input, "target": row["target"], "metadata": metadata})
        generated["datasets"][split] = repaired
    return generated


def generate(seed: int = 26080850) -> dict[str, Any]:
    return sanitize_for_training(base.generate(seed))