#!/usr/bin/env python3
"""Independent protected institution generator for the contribution study.

This file intentionally imports no EDON, ActionNet, Platform 002, training, or
model code. Its target executor is separately implemented from the training
experience engine.
"""

from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import random
from pathlib import Path
from typing import Any


EXPERIMENT_ID = "CEREBRUM-PLATFORM-CONTRIB-001"
INSTRUMENT_ID = "CEREBRUM-PLATFORM-CONTRIB-001-PROTECTED-v1.0.0"
SEED = 26082371
CASE_COUNT = 320
FACTORS = ("CAPACITY", "AUTHORITY", "DEADLINE", "UNCERTAINTY")
RENDERERS = ("RANGE_STATUS_ADVISORY", "MISSION_ASSURANCE_LOG", "LAUNCH_COMMIT_PACKET")


def canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def digest_bytes(payload: bytes) -> str:
    return "sha256:" + hashlib.sha256(payload).hexdigest()


def opaque(prefix: str, *parts: Any) -> str:
    payload = ":".join(str(part) for part in parts).encode("utf-8")
    return prefix + "-" + hashlib.sha256(payload).hexdigest()[:20]


def execute_independently(
    factors: tuple[str, ...], capacity_loss: int, recovery: int | None
) -> dict[str, Any]:
    capacity = 100.0
    authority_active = True
    risk = 0.1
    if "CAPACITY" in factors:
        capacity -= capacity_loss
    if "AUTHORITY" in factors:
        authority_active = False
    if recovery is not None:
        capacity = float(recovery)
    if "DEADLINE" in factors:
        deadline_effect = 0.2
        if "CAPACITY" in factors:
            deadline_effect *= 1.5
        if "AUTHORITY" in factors:
            deadline_effect *= 2.0
        risk += deadline_effect
    risk = round(risk, 6)
    unknown = "UNCERTAINTY" in factors
    if unknown:
        decision = "ABSTAIN"
        reasons = ["CRITICAL_EVIDENCE_UNKNOWN"]
    elif not authority_active:
        decision = "DENY"
        reasons = ["AUTHORITY_REVOKED"]
    elif capacity < 65:
        decision = "DENY"
        reasons = ["CAPACITY_BELOW_SAFETY_FLOOR"]
    elif risk >= 0.5:
        decision = "DENY"
        reasons = ["COMPOSED_RISK_EXCEEDS_LIMIT"]
    else:
        decision = "ALLOW"
        reasons = ["REGISTERED_CONSTRAINTS_SATISFIED"]
    return {
        "decision": decision,
        "risk_score": risk,
        "capacity_final": round(capacity, 6),
        "risk_band": "SAFE" if risk < 0.25 else "DEGRADED" if risk < 0.5 else "CRITICAL",
        "capacity_band": "NORMAL" if capacity >= 85 else "CONSTRAINED" if capacity >= 65 else "FAILED",
        "reason_codes": reasons,
        "binding_authority": False,
    }


def build_case(index: int, rng: random.Random) -> tuple[dict[str, Any], dict[str, Any]]:
    combinations = [
        combo for width in range(1, len(FACTORS) + 1)
        for combo in itertools.combinations(FACTORS, width)
    ]
    factors = combinations[(index * 7) % len(combinations)]
    capacity_loss = (12, 22, 32, 42, 52)[(index * 5 + index // 3) % 5]
    recovery = None
    if "CAPACITY" in factors and index % 4 == 0:
        recovery = (68, 78, 88)[index % 3]
    renderer = RENDERERS[index % len(RENDERERS)]
    horizon = (900, 21600, 172800, 2592000)[index % 4]
    case_id = opaque("protected-case", INSTRUMENT_ID, index, factors, capacity_loss, recovery)
    events = []
    if "CAPACITY" in factors:
        events.append({"mechanism": "capacity-degradation", "target_type": "RESOURCE", "operation": "DECREMENT", "value": capacity_loss, "at_seconds": 60})
    if "AUTHORITY" in factors:
        events.append({"mechanism": "authority-revocation", "target_type": "AUTHORITY", "operation": "SET", "value": False, "at_seconds": 120})
    if recovery is not None:
        events.append({"mechanism": "counterfactual-recovery", "target_type": "RESOURCE", "operation": "SET", "value": recovery, "at_seconds": 300})
    if "DEADLINE" in factors:
        events.append({"mechanism": "deadline-pressure", "target_type": "RISK", "operation": "INCREMENT", "value": 0.2, "at_seconds": min(horizon, 86400)})
    if "UNCERTAINTY" in factors:
        events.append({"mechanism": "evidence-uncertainty", "target_type": "EVIDENCE", "operation": "SET", "value": "UNKNOWN", "at_seconds": 30})
    structured = {
        "case_id": case_id,
        "institution_type": "ORBITAL_LAUNCH_RANGE",
        "institution_id": opaque("range", INSTRUMENT_ID, index % 11),
        "renderer": renderer,
        "initial_capacity": 100.0,
        "capacity_loss": capacity_loss if "CAPACITY" in factors else 0,
        "authority_revocation_present": "AUTHORITY" in factors,
        "deadline_pressure_present": "DEADLINE" in factors,
        "critical_evidence_unknown": "UNCERTAINTY" in factors,
        "decision_horizon_seconds": horizon,
        "events": events,
        "experience_origin": "INDEPENDENT_PROTECTED_INSTITUTION",
    }
    if renderer == "RANGE_STATUS_ADVISORY":
        prompt = (
            f"RANGE STATUS ADVISORY {case_id}. Orbital launch range events: {canonical(events)}. "
            f"Critical evidence unknown={structured['critical_evidence_unknown']}; horizon={horizon}. "
            "Return only the non-binding institutional decision and predicted risk/capacity certificate."
        )
    elif renderer == "MISSION_ASSURANCE_LOG":
        prompt = "MISSION_ASSURANCE_LOG\n" + json.dumps(structured, sort_keys=True, indent=2) + (
            "\nEvaluate the range state and return the exact JSON candidate certificate."
        )
    else:
        prompt = (
            "LAUNCH_COMMIT_PACKET\n" + canonical(structured)
            + "\nPredict decision, risk_score, risk_band, capacity_band, reason_codes, binding_authority."
        )
    public = {
        "case_id": case_id,
        "observation": {"structured": structured, "prompt": prompt},
        "messages": [
            {
                "role": "system",
                "content": "Return only a non-binding JSON candidate certificate for the protected institution.",
            },
            {"role": "user", "content": prompt},
        ],
        "lineage": {
            "institution_lineage": "protected-orbital-launch-range-v1",
            "generator_lineage": "independent-protected-institution-v1",
            "training_exposure": False,
        },
    }
    label = {"case_id": case_id, "target": execute_independently(factors, capacity_loss, recovery)}
    return public, label


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> str:
    payload = "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows).encode("utf-8")
    path.write_bytes(payload)
    return digest_bytes(payload)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, default=Path(__file__).with_name("protected"))
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    rng = random.Random(SEED)
    public_rows = []
    labels = []
    for index in range(CASE_COUNT):
        public, label = build_case(index, rng)
        public_rows.append(public)
        labels.append(label)
    public_hash = write_jsonl(args.output_dir / "public_inputs.jsonl", public_rows)
    label_hash = write_jsonl(args.output_dir / "labels.jsonl", labels)
    manifest = {
        "schema_version": "cerebrum-platform-contrib-protected.v1",
        "experiment_id": EXPERIMENT_ID,
        "instrument_id": INSTRUMENT_ID,
        "seed": SEED,
        "case_count": CASE_COUNT,
        "public_inputs_sha256": public_hash,
        "protected_labels_sha256": label_hash,
        "labels_separated": True,
        "imports_actionnet_or_training_code": False,
        "target_institution_type": "ORBITAL_LAUNCH_RANGE",
        "binding_authority": False,
        "claim_boundary": "Project-authored independently implemented synthetic target; not an independently held real institution.",
    }
    (args.output_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(manifest, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())