"""Three-layer reconciliation with explicit, reviewable conflicts."""

from __future__ import annotations

from collections import defaultdict
from statistics import fmean
from typing import Any, Iterable

from edon.common.hashing import canonical_json, sha256_json

from .candidate import TruthLayer
from .models import (
    CompilerSettings,
    ConflictKind,
    ConflictRecord,
    ExtractedPrimitive,
    PrimitiveType,
    ReconciledFact,
)


LAYER_ORDER = (TruthLayer.NORMATIVE, TruthLayer.OPERATIONAL, TruthLayer.BEHAVIORAL)
SENSITIVE_PRIMITIVES = {
    PrimitiveType.AUTHORITY,
    PrimitiveType.APPROVAL,
    PrimitiveType.REVOCATION,
    PrimitiveType.JURISDICTION,
    PrimitiveType.CONSEQUENCE,
}


def _unique_values(records: Iterable[ExtractedPrimitive]) -> tuple[Any, ...]:
    values: dict[str, Any] = {}
    for record in records:
        values.setdefault(canonical_json(record.value), record.value)
    return tuple(values[key] for key in sorted(values))


def _conflict(
    records: list[ExtractedPrimitive],
    kind: ConflictKind,
    values_by_layer: dict[str, tuple[Any, ...]],
) -> ConflictRecord:
    first = records[0]
    identity = {
        "fact_key": first.fact_key,
        "kind": kind.value,
        "values_by_layer": values_by_layer,
    }
    severity = "HIGH" if first.primitive_type in SENSITIVE_PRIMITIVES else "MODERATE"
    return ConflictRecord(
        conflict_id="conflict-" + sha256_json(identity).split(":", 1)[1][:20],
        mechanism_id=first.mechanism_id,
        kind=kind,
        primitive_type=first.primitive_type,
        subject=first.subject,
        predicate=first.predicate,
        values_by_layer=values_by_layer,
        source_ids=tuple(sorted({record.source_reference.source_id for record in records})),
        severity=severity,
    )


def reconcile(
    primitives: tuple[ExtractedPrimitive, ...],
    settings: CompilerSettings,
) -> tuple[tuple[ReconciledFact, ...], tuple[ConflictRecord, ...]]:
    grouped: dict[tuple[str, str, str, str], list[ExtractedPrimitive]] = defaultdict(list)
    for primitive in primitives:
        grouped[primitive.fact_key].append(primitive)

    facts: list[ReconciledFact] = []
    conflicts: list[ConflictRecord] = []
    for key in sorted(grouped):
        records = grouped[key]
        by_layer = {
            layer: [record for record in records if record.truth_layer is layer]
            for layer in LAYER_ORDER
        }
        values = {
            layer.value: _unique_values(by_layer[layer])
            for layer in LAYER_ORDER
            if by_layer[layer]
        }
        fact_conflicts: list[ConflictRecord] = []
        normative_values = values.get(TruthLayer.NORMATIVE.value, ())
        all_values = {canonical_json(value) for layer_values in values.values() for value in layer_values}
        if len(normative_values) > 1:
            fact_conflicts.append(_conflict(records, ConflictKind.NORMATIVE_CONFLICT, values))
        if len(all_values) > 1:
            fact_conflicts.append(_conflict(records, ConflictKind.CROSS_LAYER_MISMATCH, values))
        if settings.require_normative_layer and not normative_values:
            fact_conflicts.append(_conflict(records, ConflictKind.MISSING_NORMATIVE, values))

        selected_value: Any = None
        for layer in LAYER_ORDER:
            layer_values = values.get(layer.value, ())
            if len(layer_values) == 1:
                selected_value = layer_values[0]
                break

        observed_layers = tuple(layer for layer in LAYER_ORDER if by_layer[layer])
        extraction_confidence = fmean(record.confidence for record in records)
        coverage = len(observed_layers) / len(LAYER_ORDER)
        agreement = 1.0 if not fact_conflicts else 0.35
        confidence = max(0.0, min(1.0, 0.65 * extraction_confidence + 0.20 * coverage + 0.15 * agreement))
        agreement_state = (
            "CONTESTED" if fact_conflicts
            else "AGREED" if len(observed_layers) == len(LAYER_ORDER)
            else "PARTIAL_AGREEMENT"
        )
        references = {
            (record.source_reference.source_id, record.source_reference.version): record.source_reference
            for record in records
        }
        facts.append(ReconciledFact(
            mechanism_id=records[0].mechanism_id,
            primitive_type=records[0].primitive_type,
            subject=records[0].subject,
            predicate=records[0].predicate,
            selected_value=selected_value,
            agreement_state=agreement_state,
            layers=observed_layers,
            confidence=round(confidence, 6),
            statement_ids=tuple(sorted(record.statement_id for record in records)),
            source_references=tuple(references[key] for key in sorted(references)),
            conflict_ids=tuple(conflict.conflict_id for conflict in fact_conflicts),
        ))
        conflicts.extend(fact_conflicts)

    return tuple(facts), tuple(conflicts)