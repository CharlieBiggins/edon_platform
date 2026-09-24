#!/usr/bin/env python3
from __future__ import annotations

from collections import defaultdict
from typing import Any

from mlgw_program import sha256_value


SUPPORTED_CONTROLLERS = {"actual_mlgw_replay", "critical_biggest_return", "conventional_or"}


def world_fingerprints(world: dict[str, Any]) -> tuple[str, str]:
    resources = {"crews": world["crews"]}
    physical = {
        "initial_customers_out": world["initial_customers_out"],
        "jobs": world["jobs"],
    }
    return sha256_value(resources), sha256_value(physical)


def priority(job: dict[str, Any], controller_id: str) -> tuple[float, str]:
    if controller_id == "actual_mlgw_replay":
        return (float(job.get("actual_priority", 10**9)), job["job_id"])
    if controller_id == "critical_biggest_return":
        value = -(1_000_000.0 * float(job["critical_weight"]) + float(job["customers_restored"]) / float(job["duration_minutes"]))
        return (value, job["job_id"])
    if controller_id == "conventional_or":
        value = -(10_000.0 * float(job["critical_weight"]) + float(job["customers_restored"]) / max(1.0, float(job["duration_minutes"])))
        return (value, job["job_id"])
    raise ValueError(f"controller requires an external frozen runtime: {controller_id}")


def simulate(world: dict[str, Any], controller_id: str) -> dict[str, Any]:
    if controller_id not in SUPPORTED_CONTROLLERS:
        raise ValueError(f"unsupported deterministic rehearsal controller: {controller_id}")
    jobs = {job["job_id"]: dict(job) for job in world["jobs"]}
    if len(jobs) != len(world["jobs"]):
        raise ValueError("duplicate job IDs")
    unknown_dependencies = {
        dependency
        for job in jobs.values()
        for dependency in job["dependencies"]
        if dependency not in jobs
    }
    if unknown_dependencies:
        raise ValueError(f"unknown dependencies: {sorted(unknown_dependencies)}")
    crews = [dict(crew) for crew in world["crews"]]
    crew_time = {crew["crew_id"]: float(crew["available_minute"]) for crew in crews}
    completed: dict[str, float] = {}
    assignments: list[dict[str, Any]] = []
    unsafe = 0

    while len(completed) < len(jobs):
        progress = False
        for crew in sorted(crews, key=lambda value: (crew_time[value["crew_id"]], value["crew_id"])):
            crew_id = crew["crew_id"]
            now = crew_time[crew_id]
            ready = []
            for job in jobs.values():
                if job["job_id"] in completed or any(row["job_id"] == job["job_id"] for row in assignments):
                    continue
                if job["required_capability"] not in crew["capabilities"]:
                    continue
                if not job["safety_validated"]:
                    unsafe += 1
                    continue
                if any(dependency not in completed for dependency in job["dependencies"]):
                    continue
                dependency_time = max((completed[dependency] for dependency in job["dependencies"]), default=0.0)
                start = max(now, float(job["available_minute"]), dependency_time)
                ready.append((job, start, dependency_time))
            if not ready:
                future = [
                    max(float(job["available_minute"]), max((completed.get(dep, float("inf")) for dep in job["dependencies"]), default=0.0))
                    for job in jobs.values()
                    if job["job_id"] not in completed
                    and not any(row["job_id"] == job["job_id"] for row in assignments)
                    and job["required_capability"] in crew["capabilities"]
                    and all(dep in completed for dep in job["dependencies"])
                ]
                finite = [value for value in future if value != float("inf") and value > now]
                if finite:
                    crew_time[crew_id] = min(finite)
                continue
            job, start, dependency_time = min(ready, key=lambda item: (item[1], priority(item[0], controller_id)))
            finish = start + float(job["duration_minutes"])
            assignments.append({
                "crew_id": crew_id,
                "job_id": job["job_id"],
                "start_minute": start,
                "finish_minute": finish,
                "ready_minute": max(float(job["available_minute"]), dependency_time),
                "duration_minutes": float(job["duration_minutes"]),
                "customers_restored": int(job["customers_restored"]),
                "critical_weight": float(job["critical_weight"]),
            })
            crew_time[crew_id] = finish
            completed[job["job_id"]] = finish
            progress = True
        if not progress:
            unassigned = sorted(set(jobs) - set(completed) - {row["job_id"] for row in assignments})
            if unassigned:
                raise ValueError(f"simulation deadlock or missing capability: {unassigned}")

    curve = [{"minute": 0.0, "customers_out": float(world["initial_customers_out"])}]
    customers_out = float(world["initial_customers_out"])
    by_finish: dict[float, int] = defaultdict(int)
    for assignment in assignments:
        by_finish[assignment["finish_minute"]] += assignment["customers_restored"]
    for minute in sorted(by_finish):
        customers_out = max(0.0, customers_out - by_finish[minute])
        curve.append({"minute": minute, "customers_out": customers_out})
    resource_hash, physical_hash = world_fingerprints(world)
    crew_hours = sum(row["duration_minutes"] for row in assignments) / 60.0
    coordination_wait = sum(row["start_minute"] - row["ready_minute"] for row in assignments)
    critical_outage_hours = sum(row["critical_weight"] * row["finish_minute"] / 60.0 for row in assignments)
    return {
        "episode_id": f"{world['world_id']}:{controller_id}",
        "controller_id": controller_id,
        "resource_fingerprint": resource_hash,
        "physical_scenario_fingerprint": physical_hash,
        "restoration_curve": curve,
        "crew_hours": crew_hours,
        "coordination_latency_minutes": {"ready_to_assignment": coordination_wait},
        "critical_outage_hours": critical_outage_hours,
        "unsafe_recommendations": unsafe,
        "unauthorized_actions": 0,
        "assignments": assignments,
        "binding_authority": False,
        "claim_boundary": "Synthetic integration rehearsal only; not MLGW data or performance evidence."
    }