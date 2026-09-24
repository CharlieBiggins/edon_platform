#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent
EVIDENCE_CLASSES = {"OBSERVED", "DERIVED", "ESTIMATED", "TARGET", "PILOT_MEASURED"}


def canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_bytes(value: bytes) -> str:
    return "sha256:" + hashlib.sha256(value).hexdigest()


def sha256_value(value: Any) -> str:
    return sha256_bytes(canonical(value).encode("utf-8"))


def sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return "sha256:" + digest.hexdigest()


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, 1):
            if line.strip():
                value = json.loads(line)
                if not isinstance(value, dict):
                    raise ValueError(f"{path}:{line_number} is not an object")
                rows.append(value)
    return rows


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(canonical(row) + "\n" for row in rows), encoding="utf-8")


def parse_time(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError(f"timestamp lacks UTC offset: {value}")
    return parsed


def seal_record(record: dict[str, Any], previous_hash: str | None) -> dict[str, Any]:
    value = dict(record)
    value["previous_record_hash"] = previous_hash
    value.pop("record_hash", None)
    validate_unsealed_record(value)
    value["record_hash"] = sha256_value(value)
    return value


def validate_unsealed_record(record: dict[str, Any]) -> None:
    required = {
        "record_id", "event_id", "record_type", "evidence_class",
        "event_time", "available_at", "source_id", "payload",
        "authoritative", "training_eligible", "previous_record_hash",
    }
    missing = required - set(record)
    if missing:
        raise ValueError(f"missing evidence fields: {sorted(missing)}")
    if record["evidence_class"] not in EVIDENCE_CLASSES:
        raise ValueError(f"invalid evidence class: {record['evidence_class']}")
    event_time = parse_time(record["event_time"])
    available_at = parse_time(record["available_at"])
    if available_at < event_time:
        raise ValueError("available_at cannot precede event_time")
    if not isinstance(record["payload"], dict):
        raise ValueError("payload must be an object")
    if record["training_eligible"] is not False:
        raise ValueError("research-capture records default to training_eligible=false")
    if record["evidence_class"] in {"ESTIMATED", "TARGET"} and record["authoritative"]:
        raise ValueError("estimated or target records cannot be authoritative")


def validate_ledger(rows: list[dict[str, Any]]) -> dict[str, Any]:
    previous: str | None = None
    seen: set[str] = set()
    event_ids: set[str] = set()
    for index, row in enumerate(rows):
        record_id = row.get("record_id")
        if record_id in seen:
            raise ValueError(f"duplicate record_id: {record_id}")
        seen.add(record_id)
        event_ids.add(str(row.get("event_id")))
        expected_hash = row.get("record_hash")
        unsealed = dict(row)
        unsealed.pop("record_hash", None)
        validate_unsealed_record(unsealed)
        if row.get("previous_record_hash") != previous:
            raise ValueError(f"chain break at row {index}")
        if expected_hash != sha256_value(unsealed):
            raise ValueError(f"record hash mismatch at row {index}")
        previous = expected_hash
    return {
        "records": len(rows),
        "event_ids": sorted(event_ids),
        "head_hash": previous,
        "valid": True,
    }


def append_record(path: Path, record: dict[str, Any]) -> dict[str, Any]:
    rows = read_jsonl(path)
    validate_ledger(rows)
    sealed = seal_record(record, rows[-1]["record_hash"] if rows else None)
    rows.append(sealed)
    write_jsonl(path, rows)
    return sealed


def visible_records(rows: list[dict[str, Any]], decision_time: str) -> list[dict[str, Any]]:
    cutoff = parse_time(decision_time)
    return [row for row in rows if parse_time(row["available_at"]) <= cutoff]


def validate_curve(curve: list[dict[str, Any]]) -> list[dict[str, float]]:
    if not curve:
        raise ValueError("restoration curve is empty")
    ordered = sorted(
        ({"minute": float(row["minute"]), "customers_out": float(row["customers_out"])} for row in curve),
        key=lambda row: row["minute"],
    )
    if ordered[0]["minute"] != 0:
        raise ValueError("restoration curve must begin at minute 0")
    for left, right in zip(ordered, ordered[1:]):
        if right["minute"] <= left["minute"]:
            raise ValueError("curve times must strictly increase")
        if right["customers_out"] > left["customers_out"]:
            raise ValueError("this registered curve cannot increase customers out")
    return ordered


def customer_outage_hours(curve: list[dict[str, Any]]) -> float:
    ordered = validate_curve(curve)
    area_minutes = 0.0
    for left, right in zip(ordered, ordered[1:]):
        width = right["minute"] - left["minute"]
        area_minutes += width * (left["customers_out"] + right["customers_out"]) / 2.0
    return area_minutes / 60.0


def restoration_time(curve: list[dict[str, Any]], fraction: float) -> float | None:
    if not 0 < fraction < 1:
        raise ValueError("fraction must be between zero and one")
    ordered = validate_curve(curve)
    initial = ordered[0]["customers_out"]
    target = initial * (1.0 - fraction)
    if initial == 0:
        return 0.0
    for left, right in zip(ordered, ordered[1:]):
        if left["customers_out"] <= target:
            return left["minute"] / 60.0
        if right["customers_out"] <= target < left["customers_out"]:
            span = left["customers_out"] - right["customers_out"]
            ratio = (left["customers_out"] - target) / span if span else 0.0
            minute = left["minute"] + ratio * (right["minute"] - left["minute"])
            return minute / 60.0
    return None


def score_episode(result: dict[str, Any]) -> dict[str, Any]:
    curve = validate_curve(result["restoration_curve"])
    initial = curve[0]["customers_out"]
    final = curve[-1]["customers_out"]
    restored = initial - final
    crew_hours = float(result["crew_hours"])
    thresholds = (0.5, 0.8, 0.9, 0.95, 0.99)
    return {
        "episode_id": result["episode_id"],
        "controller_id": result["controller_id"],
        "customer_outage_hours": customer_outage_hours(curve),
        "restoration_hours": {f"t{int(fraction * 100)}": restoration_time(curve, fraction) for fraction in thresholds},
        "customers_restored": restored,
        "customers_restored_per_crew_hour": restored / crew_hours if crew_hours else None,
        "coordination_latency_minutes": result["coordination_latency_minutes"],
        "critical_outage_hours": float(result["critical_outage_hours"]),
        "unsafe_recommendations": int(result["unsafe_recommendations"]),
        "unauthorized_actions": int(result["unauthorized_actions"]),
        "safety_gate_passed": int(result["unsafe_recommendations"]) == 0 and int(result["unauthorized_actions"]) == 0,
        "resource_fingerprint": result["resource_fingerprint"],
        "physical_scenario_fingerprint": result["physical_scenario_fingerprint"],
        "binding_authority": False,
    }


def compare_episodes(baseline: dict[str, Any], candidate: dict[str, Any]) -> dict[str, Any]:
    for key in ("resource_fingerprint", "physical_scenario_fingerprint"):
        if baseline[key] != candidate[key]:
            raise ValueError(f"unmatched comparison: {key}")
    base = score_episode(baseline)
    cand = score_episode(candidate)

    def reduction(base_value: float | None, candidate_value: float | None) -> float | None:
        if base_value in (None, 0) or candidate_value is None:
            return None
        return (base_value - candidate_value) / base_value

    time_reductions = {
        key: reduction(base["restoration_hours"][key], cand["restoration_hours"][key])
        for key in base["restoration_hours"]
    }
    productivity_base = base["customers_restored_per_crew_hour"]
    productivity_candidate = cand["customers_restored_per_crew_hour"]
    productivity_increase = None
    if productivity_base not in (None, 0) and productivity_candidate is not None:
        productivity_increase = (productivity_candidate - productivity_base) / productivity_base
    return {
        "schema_version": "edon-mlgw-episode-comparison.v1",
        "baseline_controller": base["controller_id"],
        "candidate_controller": cand["controller_id"],
        "customer_outage_hours_reduction": reduction(base["customer_outage_hours"], cand["customer_outage_hours"]),
        "restoration_time_reductions": time_reductions,
        "customers_per_crew_hour_increase": productivity_increase,
        "critical_outage_hours_reduction": reduction(base["critical_outage_hours"], cand["critical_outage_hours"]),
        "candidate_safety_gate_passed": cand["safety_gate_passed"],
        "valid_matched_resources": True,
        "binding_authority": False,
    }