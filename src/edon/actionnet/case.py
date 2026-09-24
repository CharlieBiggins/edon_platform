"""A label-isolated ActionNet case record."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ActionNetCase:
    case_id: str
    observation: dict[str, Any]
    query: str
    task_type: str
    institution_lineage: str
    source_lineage: str

    def model_input(self) -> dict[str, Any]:
        return {"observation": self.observation, "query": self.query}