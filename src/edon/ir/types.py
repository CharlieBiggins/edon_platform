"""Minimal typed contracts for the Git-facing EDON scaffold."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class SemanticState(StrEnum):
    TRUE = "TRUE"
    FALSE = "FALSE"
    UNKNOWN = "UNKNOWN"
    MISSING = "MISSING"
    CONTESTED = "CONTESTED"
    INVALID = "INVALID"


class Decision(StrEnum):
    ALLOW = "ALLOW"
    DENY = "DENY"
    ABSTAIN = "ABSTAIN"
    CONTESTED = "CONTESTED"
    INVALID = "INVALID"


@dataclass(frozen=True)
class SourceReference:
    source_id: str
    version: str
    sha256: str
    locator: str


@dataclass(frozen=True)
class InstitutionalMechanism:
    mechanism_id: str
    version: str
    actors: tuple[str, ...] = ()
    roles: tuple[str, ...] = ()
    authority: tuple[str, ...] = ()
    policies: tuple[str, ...] = ()
    evidence_requirements: tuple[str, ...] = ()
    resources: tuple[str, ...] = ()
    workflow_steps: tuple[str, ...] = ()
    approvals: tuple[str, ...] = ()
    deadlines: tuple[str, ...] = ()
    revocations: tuple[str, ...] = ()
    jurisdictions: tuple[str, ...] = ()
    escalations: tuple[str, ...] = ()
    consequences: tuple[str, ...] = ()
    source_references: tuple[SourceReference, ...] = ()
    risk_class: str = "UNCLASSIFIED"
    approved: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)