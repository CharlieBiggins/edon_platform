"""Frozen gate result contract."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class GateResult:
    gate_id: str
    checks: dict[str, bool]

    @property
    def passed(self) -> bool:
        return bool(self.checks) and all(self.checks.values())