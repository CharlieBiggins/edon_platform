"""Active, replay-verified counterfactual generation for ActionNet Platform."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from edon.common.hashing import sha256_json

from .composition import CompositionExecutionError, replay_trajectory


class CounterfactualGenerationError(ValueError):
    """Raised when a counterfactual intervention is malformed or non-replayable."""


INTERVENTIONS = {
    "SET_ATTRIBUTE",
    "REMOVE_ATTRIBUTE",
    "SHIFT_EVENT",
    "DROP_EVENT",
    "CHANGE_EPISTEMIC_STATUS",
    "CHANGE_BEHAVIOR_PARAMETER",
}


class CounterfactualEngine:
    """Forks a stored trajectory and verifies each branch by deterministic replay."""

    def generate(
        self,
        batch_id: str,
        parent_experience_id: str,
        parent_trajectory: dict[str, Any],
        interventions: list[dict[str, Any]],
    ) -> dict[str, Any]:
        required = {"initial_state", "events", "horizon_states", "final_state_sha256"}
        if not required.issubset(parent_trajectory):
            raise CounterfactualGenerationError(
                "parent trajectory must come from an executable Platform 002 composition"
            )
        horizons = [
            {
                "horizon_id": row["horizon_id"],
                "duration_seconds": int(row["duration_seconds"]),
                "label": row["horizon_id"],
            }
            for row in parent_trajectory["horizon_states"]
        ]
        if not interventions:
            raise CounterfactualGenerationError("counterfactual batch requires interventions")
        branches = []
        branch_ids = set()
        for index, raw in enumerate(interventions):
            if not isinstance(raw, dict):
                raise CounterfactualGenerationError("counterfactual interventions must be objects")
            branch_id = str(raw.get("branch_id", f"branch-{index + 1:03d}")).strip()
            if not branch_id or branch_id in branch_ids:
                raise CounterfactualGenerationError("counterfactual branch_id values must be unique")
            branch_ids.add(branch_id)
            intervention_type = str(raw.get("type", "")).upper()
            if intervention_type not in INTERVENTIONS:
                raise CounterfactualGenerationError(
                    f"unsupported counterfactual intervention: {intervention_type}"
                )
            initial = deepcopy(parent_trajectory["initial_state"])
            events = deepcopy(parent_trajectory["events"])
            changed_paths = []
            if intervention_type in {"SET_ATTRIBUTE", "REMOVE_ATTRIBUTE"}:
                target = str(raw.get("target_object_id", ""))
                attribute = str(raw.get("attribute", ""))
                if not target or not attribute:
                    raise CounterfactualGenerationError("attribute intervention requires target and attribute")
                events.append({
                    "event_id": f"{batch_id}:{branch_id}:intervention",
                    "mechanism_ref": "COUNTERFACTUAL_INTERVENTION",
                    "target_object_id": target,
                    "attribute": attribute,
                    "operation": "SET" if intervention_type == "SET_ATTRIBUTE" else "DELETE",
                    "value": deepcopy(raw.get("value")),
                    "at_seconds": int(raw.get("at_seconds", 0)),
                    "order": -1,
                })
                changed_paths.append(f"objects.{target}.attributes.{attribute}")
            elif intervention_type in {"SHIFT_EVENT", "DROP_EVENT"}:
                event_id = str(raw.get("event_id", ""))
                matches = [event for event in events if str(event["event_id"]) == event_id]
                if len(matches) != 1:
                    raise CounterfactualGenerationError("event intervention must identify one parent event")
                if intervention_type == "DROP_EVENT":
                    events = [event for event in events if str(event["event_id"]) != event_id]
                else:
                    matches[0]["at_seconds"] = int(matches[0]["at_seconds"]) + int(raw.get("delta_seconds", 0))
                    if matches[0]["at_seconds"] < 0:
                        raise CounterfactualGenerationError("shifted event cannot occur before time zero")
                changed_paths.append(f"events.{event_id}")
            elif intervention_type == "CHANGE_EPISTEMIC_STATUS":
                target = str(raw.get("target_object_id", ""))
                if target not in initial["objects"]:
                    raise CounterfactualGenerationError("epistemic intervention target does not exist")
                initial["objects"][target]["epistemic_state"]["status"] = str(raw["status"]).upper()
                initial["objects"][target]["epistemic_state"]["confidence"] = float(raw.get("confidence", 0))
                changed_paths.append(f"objects.{target}.epistemic_state")
            else:
                target = str(raw.get("target_object_id", ""))
                parameter = str(raw.get("parameter", ""))
                if target not in initial["objects"] or "behavior_model" not in initial["objects"][target]:
                    raise CounterfactualGenerationError("behavior intervention requires an actor target")
                initial["objects"][target]["behavior_model"][parameter] = deepcopy(raw.get("value"))
                changed_paths.append(f"objects.{target}.behavior_model.{parameter}")
            try:
                trajectory = replay_trajectory(initial, events, horizons)
                replay = replay_trajectory(initial, trajectory["events"], horizons)
            except CompositionExecutionError as exc:
                raise CounterfactualGenerationError(str(exc)) from exc
            branch = {
                "branch_id": branch_id,
                "intervention": deepcopy(raw),
                "changed_paths": changed_paths,
                "trajectory": trajectory,
                "verification": {
                    "deterministic_replay": replay["final_state_sha256"] == trajectory["final_state_sha256"],
                    "parent_final_state_sha256": parent_trajectory["final_state_sha256"],
                    "branch_final_state_sha256": trajectory["final_state_sha256"],
                    "outcome_changed": trajectory["final_state_sha256"] != parent_trajectory["final_state_sha256"],
                },
            }
            branch["branch_sha256"] = sha256_json(branch)
            branches.append(branch)
        record = {
            "schema_version": "actionnet-counterfactual-batch.v1",
            "batch_id": str(batch_id),
            "parent_experience_id": str(parent_experience_id),
            "parent_trajectory_sha256": sha256_json(parent_trajectory),
            "branches": branches,
            "all_branches_replay_verified": all(
                branch["verification"]["deterministic_replay"] for branch in branches
            ),
            "authoritative": False,
            "binding_authority": False,
        }
        record["batch_sha256"] = sha256_json(record)
        return record