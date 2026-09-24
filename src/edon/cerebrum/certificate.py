"""Non-authoritative institutional certificate."""

from __future__ import annotations

from dataclasses import dataclass

from edon.ir import Decision, SemanticState


@dataclass(frozen=True)
class Certificate:
    semantic_state: SemanticState
    decision: Decision
    failed_conditions: tuple[str, ...] = ()
    confidence: float | None = None
    binding_authority: bool = False

    def __post_init__(self) -> None:
        if self.binding_authority:
            raise ValueError("Cerebrum certificates cannot carry binding authority")