"""Typed inputs and intermediate records for the Institution Compiler."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from edon.ir import SourceReference

from .candidate import TruthLayer


class SourceFormat(StrEnum):
    STRUCTURED_JSON = "STRUCTURED_JSON"
    EDON_ANNOTATED_TEXT = "EDON_ANNOTATED_TEXT"


class PrimitiveType(StrEnum):
    ACTOR = "ACTOR"
    ROLE = "ROLE"
    AUTHORITY = "AUTHORITY"
    POLICY = "POLICY"
    EVIDENCE_REQUIREMENT = "EVIDENCE_REQUIREMENT"
    RESOURCE = "RESOURCE"
    WORKFLOW_STEP = "WORKFLOW_STEP"
    APPROVAL = "APPROVAL"
    DEADLINE = "DEADLINE"
    REVOCATION = "REVOCATION"
    JURISDICTION = "JURISDICTION"
    ESCALATION = "ESCALATION"
    CONSEQUENCE = "CONSEQUENCE"


class RiskClass(StrEnum):
    UNCLASSIFIED = "UNCLASSIFIED"
    LOW = "LOW"
    MODERATE = "MODERATE"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class ConflictKind(StrEnum):
    NORMATIVE_CONFLICT = "NORMATIVE_CONFLICT"
    CROSS_LAYER_MISMATCH = "CROSS_LAYER_MISMATCH"
    MISSING_NORMATIVE = "MISSING_NORMATIVE"


@dataclass(frozen=True)
class SourceDocument:
    source_id: str
    version: str
    truth_layer: TruthLayer
    kind: str
    source_format: SourceFormat
    content: Any
    reference: SourceReference
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ExtractedPrimitive:
    statement_id: str
    mechanism_id: str
    primitive_type: PrimitiveType
    subject: str
    predicate: str
    value: Any
    truth_layer: TruthLayer
    source_reference: SourceReference
    confidence: float
    risk_class: RiskClass
    source_span: str

    @property
    def fact_key(self) -> tuple[str, str, str, str]:
        return (
            self.mechanism_id,
            self.primitive_type.value,
            self.subject.strip().casefold(),
            self.predicate.strip().casefold(),
        )


@dataclass(frozen=True)
class ConflictRecord:
    conflict_id: str
    mechanism_id: str
    kind: ConflictKind
    primitive_type: PrimitiveType
    subject: str
    predicate: str
    values_by_layer: dict[str, tuple[Any, ...]]
    source_ids: tuple[str, ...]
    severity: str
    requires_review: bool = True


@dataclass(frozen=True)
class ReconciledFact:
    mechanism_id: str
    primitive_type: PrimitiveType
    subject: str
    predicate: str
    selected_value: Any
    agreement_state: str
    layers: tuple[TruthLayer, ...]
    confidence: float
    statement_ids: tuple[str, ...]
    source_references: tuple[SourceReference, ...]
    conflict_ids: tuple[str, ...] = ()


@dataclass(frozen=True)
class CompilerSettings:
    minimum_review_confidence: float = 0.9
    require_normative_layer: bool = True

    def __post_init__(self) -> None:
        if not 0.0 <= self.minimum_review_confidence <= 1.0:
            raise ValueError("minimum_review_confidence must be between zero and one")


@dataclass(frozen=True)
class CompilerInput:
    schema_version: str
    compiler_run_id: str
    institution_id: str
    institution_version: str
    sources: tuple[SourceDocument, ...]
    settings: CompilerSettings
    raw_input: dict[str, Any]