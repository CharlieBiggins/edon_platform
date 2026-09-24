"""Safe loading and hashing of compiler input bundles."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from edon.common.hashing import sha256_bytes, sha256_json
from edon.ir import SourceReference

from .candidate import TruthLayer
from .models import CompilerInput, CompilerSettings, SourceDocument, SourceFormat


class CompilerInputError(ValueError):
    """Raised when compiler input cannot be safely or deterministically loaded."""


def _required_string(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise CompilerInputError(f"{field} must be a non-empty string")
    return value.strip()


def _load_source_content(row: dict[str, Any], base_dir: Path) -> tuple[Any, str, str]:
    has_content = "content" in row
    has_path = "path" in row
    if has_content == has_path:
        raise CompilerInputError("each source must define exactly one of content or path")
    if has_content:
        content = row["content"]
        return content, str(row.get("locator", "inline")), sha256_json(content)

    relative = Path(_required_string(row["path"], "source.path"))
    if relative.is_absolute() or ".." in relative.parts:
        raise CompilerInputError("source.path must stay within the input bundle directory")
    source_path = (base_dir / relative).resolve()
    try:
        source_path.relative_to(base_dir.resolve())
    except ValueError as exc:
        raise CompilerInputError("source.path escapes the input bundle directory") from exc
    if not source_path.is_file():
        raise CompilerInputError(f"source file does not exist: {relative.as_posix()}")
    payload = source_path.read_bytes()
    source_format = SourceFormat(row.get("format", "STRUCTURED_JSON"))
    if source_format is SourceFormat.STRUCTURED_JSON:
        try:
            content = json.loads(payload.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise CompilerInputError(f"invalid structured source: {relative.as_posix()}") from exc
    else:
        try:
            content = payload.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise CompilerInputError(f"annotated source is not UTF-8: {relative.as_posix()}") from exc
    return content, str(row.get("locator", relative.as_posix())), sha256_bytes(payload)


def load_compiler_input(path: Path) -> CompilerInput:
    """Load a compiler bundle and verify every source before extraction."""

    path = path.resolve()
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise CompilerInputError(f"cannot read compiler input: {path}") from exc
    if not isinstance(raw, dict):
        raise CompilerInputError("compiler input must be a JSON object")
    if raw.get("schema_version") != "edon-institution-compiler-input.v1":
        raise CompilerInputError("unsupported compiler input schema_version")

    source_rows = raw.get("sources")
    if not isinstance(source_rows, list) or not source_rows:
        raise CompilerInputError("sources must be a non-empty array")
    seen: set[tuple[str, str]] = set()
    sources: list[SourceDocument] = []
    for index, source_row in enumerate(source_rows):
        if not isinstance(source_row, dict):
            raise CompilerInputError(f"sources[{index}] must be an object")
        source_id = _required_string(source_row.get("source_id"), f"sources[{index}].source_id")
        version = _required_string(source_row.get("version"), f"sources[{index}].version")
        identity = (source_id, version)
        if identity in seen:
            raise CompilerInputError(f"duplicate source identity: {source_id}@{version}")
        seen.add(identity)
        try:
            layer = TruthLayer(source_row.get("truth_layer"))
            source_format = SourceFormat(source_row.get("format", "STRUCTURED_JSON"))
        except ValueError as exc:
            raise CompilerInputError(f"sources[{index}] has an unsupported layer or format") from exc
        content, locator, digest = _load_source_content(source_row, path.parent)
        declared_digest = source_row.get("sha256")
        if declared_digest is not None and declared_digest != digest:
            raise CompilerInputError(f"source hash mismatch: {source_id}@{version}")
        reference = SourceReference(source_id, version, digest, locator)
        metadata = source_row.get("metadata", {})
        if not isinstance(metadata, dict):
            raise CompilerInputError(f"sources[{index}].metadata must be an object")
        sources.append(SourceDocument(
            source_id=source_id,
            version=version,
            truth_layer=layer,
            kind=_required_string(source_row.get("kind", "UNSPECIFIED"), f"sources[{index}].kind"),
            source_format=source_format,
            content=content,
            reference=reference,
            metadata=metadata,
        ))

    settings_row = raw.get("settings", {})
    if not isinstance(settings_row, dict):
        raise CompilerInputError("settings must be an object")
    require_normative_layer = settings_row.get("require_normative_layer", True)
    minimum_review_confidence = settings_row.get("minimum_review_confidence", 0.9)
    if not isinstance(require_normative_layer, bool):
        raise CompilerInputError("require_normative_layer must be boolean")
    if isinstance(minimum_review_confidence, bool) or not isinstance(minimum_review_confidence, (int, float)):
        raise CompilerInputError("minimum_review_confidence must be numeric")
    try:
        settings = CompilerSettings(
            minimum_review_confidence=float(minimum_review_confidence),
            require_normative_layer=require_normative_layer,
        )
    except (TypeError, ValueError) as exc:
        raise CompilerInputError("invalid compiler settings") from exc
    return CompilerInput(
        schema_version=_required_string(raw.get("schema_version"), "schema_version"),
        compiler_run_id=_required_string(raw.get("compiler_run_id"), "compiler_run_id"),
        institution_id=_required_string(raw.get("institution_id"), "institution_id"),
        institution_version=_required_string(raw.get("institution_version"), "institution_version"),
        sources=tuple(sources),
        settings=settings,
        raw_input=raw,
    )