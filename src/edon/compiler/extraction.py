"""Deterministic extractors for structured and EDON-annotated sources."""

from __future__ import annotations

import csv
import io
from typing import Any

from edon.common.hashing import sha256_json

from .ingestion import CompilerInputError
from .models import ExtractedPrimitive, PrimitiveType, RiskClass, SourceDocument, SourceFormat


ANNOTATED_FIELDS = 8


def _primitive_from_row(source: SourceDocument, row: dict[str, Any], index: int, span: str) -> ExtractedPrimitive:
    required = ("mechanism_id", "primitive_type", "subject", "predicate", "value")
    missing = [field for field in required if field not in row]
    if missing:
        raise CompilerInputError(f"{source.source_id} statement {index} missing: {', '.join(missing)}")
    try:
        primitive_type = PrimitiveType(str(row["primitive_type"]))
        risk_class = RiskClass(str(row.get("risk_class", "UNCLASSIFIED")))
    except ValueError as exc:
        raise CompilerInputError(f"{source.source_id} statement {index} has an invalid enum") from exc
    confidence = float(row.get("confidence", 1.0))
    if not 0.0 <= confidence <= 1.0:
        raise CompilerInputError(f"{source.source_id} statement {index} confidence is out of range")
    mechanism_id = str(row["mechanism_id"]).strip()
    subject = str(row["subject"]).strip()
    predicate = str(row["predicate"]).strip()
    if not mechanism_id or not subject or not predicate:
        raise CompilerInputError(f"{source.source_id} statement {index} contains an empty key field")
    normalized = {
        "source_id": source.source_id,
        "version": source.version,
        "index": index,
        "mechanism_id": mechanism_id,
        "primitive_type": primitive_type.value,
        "subject": subject,
        "predicate": predicate,
        "value": row["value"],
    }
    statement_id = "statement-" + sha256_json(normalized).split(":", 1)[1][:20]
    return ExtractedPrimitive(
        statement_id=statement_id,
        mechanism_id=mechanism_id,
        primitive_type=primitive_type,
        subject=subject,
        predicate=predicate,
        value=row["value"],
        truth_layer=source.truth_layer,
        source_reference=source.reference,
        confidence=confidence,
        risk_class=risk_class,
        source_span=span,
    )


def _structured_rows(source: SourceDocument) -> list[dict[str, Any]]:
    content = source.content
    rows = content.get("statements") if isinstance(content, dict) else content
    if not isinstance(rows, list):
        raise CompilerInputError(f"{source.source_id} structured content must contain a statements array")
    if not all(isinstance(row, dict) for row in rows):
        raise CompilerInputError(f"{source.source_id} statements must be objects")
    return rows


def _annotated_rows(source: SourceDocument) -> list[dict[str, Any]]:
    if not isinstance(source.content, str):
        raise CompilerInputError(f"{source.source_id} annotated content must be text")
    rows: list[dict[str, Any]] = []
    reader = csv.reader(io.StringIO(source.content), delimiter="|")
    for line_number, fields in enumerate(reader, start=1):
        if not fields or not "".join(fields).strip() or fields[0].lstrip().startswith("#"):
            continue
        if len(fields) != ANNOTATED_FIELDS or fields[0].strip() != "EDON":
            raise CompilerInputError(
                f"{source.source_id} line {line_number} must have "
                "EDON|mechanism|type|subject|predicate|value|confidence|risk"
            )
        rows.append({
            "mechanism_id": fields[1].strip(),
            "primitive_type": fields[2].strip(),
            "subject": fields[3].strip(),
            "predicate": fields[4].strip(),
            "value": fields[5].strip(),
            "confidence": fields[6].strip(),
            "risk_class": fields[7].strip() or "UNCLASSIFIED",
            "_line": line_number,
        })
    return rows


def extract_source(source: SourceDocument) -> tuple[ExtractedPrimitive, ...]:
    if source.source_format is SourceFormat.STRUCTURED_JSON:
        rows = _structured_rows(source)
        return tuple(
            _primitive_from_row(source, row, index, f"statements/{index}")
            for index, row in enumerate(rows)
        )
    rows = _annotated_rows(source)
    return tuple(
        _primitive_from_row(source, row, index, f"line/{row['_line']}")
        for index, row in enumerate(rows)
    )


def extract_all(sources: tuple[SourceDocument, ...]) -> tuple[ExtractedPrimitive, ...]:
    primitives: list[ExtractedPrimitive] = []
    for source in sources:
        primitives.extend(extract_source(source))
    if not primitives:
        raise CompilerInputError("no institutional primitives were extracted")
    return tuple(primitives)