"""Conflict-preserving compiler candidates."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from edon.ir import InstitutionalMechanism, SourceReference


class TruthLayer(StrEnum):
    NORMATIVE = "NORMATIVE"
    OPERATIONAL = "OPERATIONAL"
    BEHAVIORAL = "BEHAVIORAL"


@dataclass(frozen=True)
class CompilerCandidate:
    candidate_id: str
    mechanism: InstitutionalMechanism
    sources: tuple[SourceReference, ...]
    observed_layers: tuple[TruthLayer, ...]
    confidence: float
    conflicts: tuple[str, ...] = ()
    required_reviewer_role: str = "INSTITUTIONAL_REVIEWER"
    qualification_checks: tuple[str, ...] = ()
    review_threshold: float = 0.9
    binding_authority: bool = False

    def __post_init__(self) -> None:
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("candidate confidence must be between zero and one")
        if not 0.0 <= self.review_threshold <= 1.0:
            raise ValueError("candidate review threshold must be between zero and one")
        if self.binding_authority:
            raise ValueError("compiler candidates cannot have binding authority")
        if self.mechanism.approved:
            raise ValueError("compiler candidates must be unapproved")

    @property
    def human_review_required(self) -> bool:
        return (
            bool(self.conflicts)
            or self.confidence < self.review_threshold
            or self.mechanism.risk_class in {"HIGH", "CRITICAL"}
        )