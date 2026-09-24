"""Deterministic bounded procedural institution generation for ActionNet Studio."""

from __future__ import annotations

import random
from typing import Any

from edon.common.hashing import sha256_json


class WorldGenerationError(RuntimeError):
    """Raised when a procedural world request is malformed or excessive."""


def _bounded(value: Any, label: str, minimum: int, maximum: int) -> int:
    try:
        result = int(value)
    except (TypeError, ValueError) as exc:
        raise WorldGenerationError(f"{label} must be an integer") from exc
    if not minimum <= result <= maximum:
        raise WorldGenerationError(f"{label} must be between {minimum} and {maximum}")
    return result


class ProceduralInstitutionGenerator:
    """Creates reproducible typed blueprints; output is synthetic and non-authoritative."""

    ADVERSARIAL_PATTERNS = (
        "AMBIGUOUS_AUTHORITY",
        "CONFLICTING_POLICY",
        "CORRUPTED_EVIDENCE",
        "HIDDEN_DEPENDENCY",
        "MISALIGNED_INCENTIVE",
        "RESOURCE_HOARDING",
        "STALE_STATE",
        "STRATEGIC_DECEPTION",
    )

    def generate(
        self,
        blueprint_id: str,
        specification: dict[str, Any],
        *,
        seed: int,
        adversarial: bool = False,
    ) -> dict[str, Any]:
        if not isinstance(specification, dict):
            raise WorldGenerationError("world specification must be an object")
        departments = _bounded(specification.get("departments", 3), "departments", 1, 100)
        actors = _bounded(specification.get("actors", departments * 3), "actors", 1, 10_000)
        resources = _bounded(specification.get("resources", departments * 2), "resources", 1, 2_000)
        policies = _bounded(specification.get("policies", departments * 2), "policies", 1, 5_000)
        workflows = _bounded(specification.get("workflows", departments * 2), "workflows", 1, 5_000)
        authority_levels = _bounded(
            specification.get("authority_levels", min(4, departments)),
            "authority_levels", 1, 20,
        )
        goals = _bounded(specification.get("goals", max(1, departments // 2)), "goals", 1, 500)
        rng = random.Random(int(seed))
        department_rows = [
            {"department_id": f"dept-{index:03d}", "name": f"Department {index:03d}"}
            for index in range(1, departments + 1)
        ]
        actor_rows = []
        for index in range(1, actors + 1):
            department = department_rows[(index - 1) % departments]["department_id"]
            actor_rows.append(
                {
                    "actor_id": f"actor-{index:05d}",
                    "department_id": department,
                    "authority_level": 1 + rng.randrange(authority_levels),
                    "capabilities": [
                        f"capability-{1 + rng.randrange(max(2, departments)):03d}"
                    ],
                    "availability": round(0.65 + rng.random() * 0.35, 6),
                }
            )
        resource_rows = [
            {
                "resource_id": f"resource-{index:04d}",
                "owner_department_id": department_rows[(index - 1) % departments]["department_id"],
                "capacity": 10 + rng.randrange(991),
                "renewable": bool(index % 2),
            }
            for index in range(1, resources + 1)
        ]
        policy_rows = [
            {
                "policy_id": f"policy-{index:04d}",
                "authority_level_required": 1 + rng.randrange(authority_levels),
                "effect": "REVIEW" if index % 3 == 0 else "ALLOW_WITH_CONSTRAINTS",
                "priority": index,
            }
            for index in range(1, policies + 1)
        ]
        workflow_rows = []
        for index in range(1, workflows + 1):
            dependency = f"workflow-{index - 1:04d}" if index > 1 and index % 2 == 0 else None
            workflow_rows.append(
                {
                    "workflow_id": f"workflow-{index:04d}",
                    "department_id": department_rows[(index - 1) % departments]["department_id"],
                    "dependencies": [dependency] if dependency else [],
                    "deadline_units": 1 + rng.randrange(168),
                }
            )
        goal_rows = [
            {
                "goal_id": f"goal-{index:03d}",
                "priority": 1 + rng.randrange(100),
                "owner_department_id": department_rows[(index - 1) % departments]["department_id"],
            }
            for index in range(1, goals + 1)
        ]
        patterns = []
        if adversarial:
            count = min(len(self.ADVERSARIAL_PATTERNS), max(2, departments // 2))
            patterns = sorted(rng.sample(list(self.ADVERSARIAL_PATTERNS), count))
        world = {
            "schema_version": "actionnet-procedural-world.v1",
            "blueprint_id": str(blueprint_id),
            "generator_seed": int(seed),
            "institution_type": str(specification.get("institution_type", "PROCEDURAL")),
            "departments": department_rows,
            "actors": actor_rows,
            "resources": resource_rows,
            "policies": policy_rows,
            "workflows": workflow_rows,
            "goals": goal_rows,
            "authority_levels": authority_levels,
            "external_constraints": list(specification.get("external_constraints", [])),
            "adversarial_patterns": patterns,
            "synthetic": True,
            "source_grounded": False,
            "authoritative": False,
            "training_eligible": False,
            "binding_authority": False,
        }
        world["world_sha256"] = sha256_json(world)
        return world