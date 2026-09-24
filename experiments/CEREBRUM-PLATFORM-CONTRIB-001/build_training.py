#!/usr/bin/env python3
"""Build matched ActionNet Platform 002 contribution conditions.

The control contains count-matched single-mechanism experience. The treatment
contains executable compositions and replay-verified counterfactual branches.
Both conditions use the same Institutional IR grammar, domains, renderers,
record count, and target function.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import sys
from copy import deepcopy
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from edon.actionnet.product import CounterfactualEngine, InstitutionalIRValidator, MechanismCompositionEngine


EXPERIMENT_ID = "CEREBRUM-PLATFORM-CONTRIB-001"
SEED = 26082331
COUNT_PER_CONDITION = 800
TRAIN_DOMAINS = ("LOGISTICS", "HEALTHCARE", "BANKING", "MANUFACTURING")
RENDERERS = ("OPERATIONS_MEMO", "STATE_REGISTER", "INCIDENT_BRIEF", "EXECUTIVE_PACKET")
FACTORS = ("CAPACITY", "AUTHORITY", "DEADLINE", "UNCERTAINTY")


def canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def digest_bytes(payload: bytes) -> str:
    return "sha256:" + hashlib.sha256(payload).hexdigest()


def digest(value: Any) -> str:
    return digest_bytes(canonical(value).encode("utf-8"))


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> str:
    payload = "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows).encode("utf-8")
    path.write_bytes(payload)
    return digest_bytes(payload)


def institutional_ir(case_id: str, domain: str, uncertainty: bool, horizons: list[int]) -> dict[str, Any]:
    return InstitutionalIRValidator().normalize({
        "institution_id": f"train-{domain.lower()}-{case_id}",
        "version": "1.0.0",
        "institution_type": domain,
        "objects": [
            {"object_id": "institution", "object_type": "INSTITUTION", "attributes": {"domain": domain}},
            {"object_id": "capacity", "object_type": "RESOURCE", "attributes": {"available": 100.0}},
            {"object_id": "authority", "object_type": "AUTHORITY", "attributes": {"active": True}},
            {"object_id": "risk", "object_type": "RISK", "attributes": {"score": 0.1}},
            {
                "object_id": "evidence", "object_type": "EVIDENCE",
                "attributes": {"status": "UNKNOWN" if uncertainty else "KNOWN"},
                "epistemic_state": {
                    "status": "UNKNOWN" if uncertainty else "KNOWN",
                    "confidence": 0.0 if uncertainty else 1.0,
                    "critical": True,
                },
            },
            {"object_id": "deadline", "object_type": "TEMPORAL_CONSTRAINT", "attributes": {"seconds": horizons[-1]}},
            {"object_id": "outcome", "object_type": "OUTCOME", "attributes": {"status": "PENDING"}},
        ],
        "horizons": [
            {"horizon_id": f"horizon-{seconds}", "duration_seconds": seconds, "label": f"{seconds} seconds"}
            for seconds in horizons
        ],
    })


def mechanism(mechanism_id: str, transition: dict[str, Any]) -> dict[str, Any]:
    return {
        "mechanism_id": mechanism_id,
        "version": "1.0.0",
        "specification": {
            "preconditions": [], "state_transitions": [transition], "dependencies": [],
            "interventions": [], "failure_modes": [], "expected_outcomes": [],
        },
    }


def mechanisms_for(factors: list[str], capacity_loss: int, deadline_at: int) -> list[dict[str, Any]]:
    rows = []
    if "CAPACITY" in factors:
        rows.append(mechanism("capacity-degradation", {
            "target_object_id": "capacity", "attribute": "available",
            "operation": "DECREMENT", "value": capacity_loss, "at_seconds": 60,
        }))
    if "AUTHORITY" in factors:
        rows.append(mechanism("authority-revocation", {
            "target_object_id": "authority", "attribute": "active",
            "operation": "SET", "value": False, "at_seconds": 120,
        }))
    if "DEADLINE" in factors:
        rows.append(mechanism("deadline-pressure", {
            "target_object_id": "risk", "attribute": "score",
            "operation": "INCREMENT", "value": 0.2, "at_seconds": deadline_at,
        }))
    if "UNCERTAINTY" in factors:
        rows.append(mechanism("evidence-uncertainty", {
            "target_object_id": "evidence", "attribute": "status",
            "operation": "SET", "value": "UNKNOWN", "at_seconds": 30,
        }))
    return rows


def edges_for(factors: list[str]) -> list[dict[str, Any]]:
    edges = []
    if "CAPACITY" in factors and "DEADLINE" in factors:
        edges.append({
            "edge_id": "capacity-amplifies-deadline",
            "source": {"mechanism_id": "capacity-degradation", "version": "1.0.0"},
            "target": {"mechanism_id": "deadline-pressure", "version": "1.0.0"},
            "relation_type": "AMPLIFIES", "conditions": {"magnitude_multiplier": 1.5},
        })
    if "AUTHORITY" in factors and "DEADLINE" in factors:
        edges.append({
            "edge_id": "authority-amplifies-deadline",
            "source": {"mechanism_id": "authority-revocation", "version": "1.0.0"},
            "target": {"mechanism_id": "deadline-pressure", "version": "1.0.0"},
            "relation_type": "AMPLIFIES", "conditions": {"magnitude_multiplier": 2.0},
        })
    return edges


def target_from_trajectory(trajectory: dict[str, Any], uncertainty: bool) -> dict[str, Any]:
    final = trajectory["final_state"]["objects"]
    capacity = float(final["capacity"]["attributes"]["available"])
    authority = bool(final["authority"]["attributes"]["active"])
    risk = round(float(final["risk"]["attributes"]["score"]), 6)
    if uncertainty:
        decision = "ABSTAIN"
        reasons = ["CRITICAL_EVIDENCE_UNKNOWN"]
    elif not authority:
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
    risk_band = "SAFE" if risk < 0.25 else "DEGRADED" if risk < 0.5 else "CRITICAL"
    capacity_band = "NORMAL" if capacity >= 85 else "CONSTRAINED" if capacity >= 65 else "FAILED"
    return {
        "decision": decision,
        "risk_score": risk,
        "capacity_final": round(capacity, 6),
        "risk_band": risk_band,
        "capacity_band": capacity_band,
        "reason_codes": reasons,
        "binding_authority": False,
    }


def observation_from(
    case_id: str,
    domain: str,
    renderer: str,
    factors: list[str],
    capacity_loss: int,
    deadline_at: int,
    trajectory: dict[str, Any],
    origin: str,
) -> dict[str, Any]:
    events = [
        {
            "mechanism": event["mechanism_ref"],
            "operation": event["operation"],
            "target_type": trajectory["initial_state"]["objects"][event["target_object_id"]]["object_type"],
            "attribute": event["attribute"],
            "value": event.get("value"),
            "at_seconds": event["at_seconds"],
        }
        for event in trajectory["events"]
    ]
    structured = {
        "case_id": case_id,
        "institution_type": domain,
        "renderer": renderer,
        "initial_capacity": 100.0,
        "capacity_loss": capacity_loss if "CAPACITY" in factors else 0,
        "authority_revocation_present": "AUTHORITY" in factors,
        "deadline_pressure_present": "DEADLINE" in factors,
        "critical_evidence_unknown": "UNCERTAINTY" in factors,
        "decision_horizon_seconds": max(row["duration_seconds"] for row in trajectory["horizon_states"]),
        "events": events,
        "experience_origin": origin,
    }
    if renderer == "OPERATIONS_MEMO":
        prompt = (
            f"Operations memo for a {domain.lower()} institution. Initial capacity is 100. "
            f"Registered events: {canonical(events)}. Critical evidence unknown: "
            f"{structured['critical_evidence_unknown']}. Evaluate the final institutional decision "
            "and predicted risk/capacity bands. Return only the registered JSON certificate."
        )
    elif renderer == "STATE_REGISTER":
        prompt = "STATE_REGISTER\n" + json.dumps(structured, sort_keys=True, indent=2) + (
            "\nCompute the final non-binding certificate as JSON."
        )
    elif renderer == "INCIDENT_BRIEF":
        prompt = (
            f"INCIDENT {case_id}: domain={domain}; horizon={structured['decision_horizon_seconds']}; "
            f"events={canonical(events)}; evidence_unknown={structured['critical_evidence_unknown']}. "
            "Predict decision, risk_score, risk_band, capacity_band, reason_codes, binding_authority."
        )
    else:
        prompt = (
            "EXECUTIVE_PACKET\nInstitutional event sequence follows.\n"
            + canonical(structured)
            + "\nReturn the exact candidate certificate."
        )
    return {"structured": structured, "prompt": prompt}


def build_record(index: int, condition: str, rng: random.Random) -> dict[str, Any]:
    domain = TRAIN_DOMAINS[index % len(TRAIN_DOMAINS)]
    renderer = RENDERERS[(index // len(TRAIN_DOMAINS)) % len(RENDERERS)]
    if condition == "CONTROL_SINGLE_MECHANISM":
        factors = [FACTORS[index % len(FACTORS)]]
    else:
        if index < COUNT_PER_CONDITION // 4:
            factors = [FACTORS[index % len(FACTORS)]]
        else:
            width = 2 + (index % 3)
            factors = sorted(rng.sample(list(FACTORS), width))
    capacity_loss = (10, 20, 30, 40, 50)[(index * 3) % 5]
    deadline_at = (600, 3600, 86400)[index % 3]
    horizons = sorted({600, 86400, deadline_at})
    uncertainty = "UNCERTAINTY" in factors
    ir = institutional_ir(f"{condition.lower()}-{index:04d}", domain, uncertainty, horizons)
    mechanisms = mechanisms_for(factors, capacity_loss, deadline_at)
    run = MechanismCompositionEngine().compose(
        f"{condition.lower()}-{index:04d}", ir, mechanisms, edges_for(factors), seed=SEED + index
    )
    trajectory = run["trajectory"]
    origin = "SINGLE_MECHANISM"
    if condition == "PLATFORM002_ACTIVE" and len(factors) > 1:
        origin = "COMPOSITION"
        if index % 2 == 0:
            capacity_events = [
                event for event in trajectory["events"]
                if event["target_object_id"] == "capacity"
            ]
            if capacity_events:
                batch = CounterfactualEngine().generate(
                    f"cf-{index:04d}", f"parent-{index:04d}", trajectory,
                    [{
                        "branch_id": "partial-recovery", "type": "SET_ATTRIBUTE",
                        "target_object_id": "capacity", "attribute": "available",
                        "value": 75.0 + (index % 3) * 10, "at_seconds": 300,
                    }],
                )
                trajectory = batch["branches"][0]["trajectory"]
                origin = "COUNTERFACTUAL"
    case_id = f"{condition.lower()}-{index:04d}-{digest([domain, factors, capacity_loss, renderer])[-10:]}"
    observation = observation_from(
        case_id, domain, renderer, factors, capacity_loss, deadline_at, trajectory, origin
    )
    target = target_from_trajectory(trajectory, uncertainty)
    return {
        "record_id": case_id,
        "condition": condition,
        "observation": observation,
        "target": target,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are Cerebrum in a protected synthetic contribution experiment. "
                    "Return only a non-binding JSON candidate certificate."
                ),
            },
            {"role": "user", "content": observation["prompt"]},
            {"role": "assistant", "content": canonical(target)},
        ],
        "lineage": {
            "institution_lineage": f"train-{domain.lower()}-platform-contrib-001",
            "generator_lineage": "actionnet-platform-002-active" if condition == "PLATFORM002_ACTIVE" else "actionnet-platform-002-single-mechanism-control",
            "protected_target_exposure": False,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, default=Path(__file__).with_name("training"))
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    conditions = {}
    for offset, condition in enumerate(("CONTROL_SINGLE_MECHANISM", "PLATFORM002_ACTIVE")):
        rng = random.Random(SEED + offset)
        rows = [build_record(index, condition, rng) for index in range(COUNT_PER_CONDITION)]
        path = args.output_dir / ("control.jsonl" if offset == 0 else "platform002.jsonl")
        conditions[condition] = {
            "path": path.name,
            "records": len(rows),
            "sha256": write_jsonl(path, rows),
            "class_counts": {
                decision: sum(row["target"]["decision"] == decision for row in rows)
                for decision in ("ALLOW", "DENY", "ABSTAIN")
            },
            "origin_counts": {
                origin: sum(row["observation"]["structured"]["experience_origin"] == origin for row in rows)
                for origin in ("SINGLE_MECHANISM", "COMPOSITION", "COUNTERFACTUAL")
            },
        }
    manifest = {
        "schema_version": "cerebrum-platform-contrib-training.v1",
        "experiment_id": EXPERIMENT_ID,
        "seed": SEED,
        "conditions": conditions,
        "matched_record_count": conditions["CONTROL_SINGLE_MECHANISM"]["records"] == conditions["PLATFORM002_ACTIVE"]["records"],
        "protected_target_used": False,
        "binding_authority": False,
        "claim_boundary": "Project-authored synthetic training conditions; no learned Cerebrum result.",
    }
    (args.output_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(manifest, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())