"""End-to-end Institution Compiler pipeline."""

from __future__ import annotations

import json
from collections import defaultdict
from dataclasses import asdict
from pathlib import Path
from statistics import fmean
from typing import Any

from edon.common.hashing import canonical_json, sha256_json
from edon.ir import InstitutionalMechanism, SourceReference

from .candidate import CompilerCandidate, TruthLayer
from .extraction import extract_all
from .ingestion import CompilerInputError, load_compiler_input
from .models import ConflictRecord, ExtractedPrimitive, PrimitiveType, ReconciledFact, RiskClass
from .reconciliation import reconcile


COMPILER_VERSION = "0.1.0"
RISK_ORDER = {
    RiskClass.UNCLASSIFIED: 0,
    RiskClass.LOW: 1,
    RiskClass.MODERATE: 2,
    RiskClass.HIGH: 3,
    RiskClass.CRITICAL: 4,
}
IR_FIELDS = {
    PrimitiveType.ACTOR: "actors",
    PrimitiveType.ROLE: "roles",
    PrimitiveType.AUTHORITY: "authority",
    PrimitiveType.POLICY: "policies",
    PrimitiveType.EVIDENCE_REQUIREMENT: "evidence_requirements",
    PrimitiveType.RESOURCE: "resources",
    PrimitiveType.WORKFLOW_STEP: "workflow_steps",
    PrimitiveType.APPROVAL: "approvals",
    PrimitiveType.DEADLINE: "deadlines",
    PrimitiveType.REVOCATION: "revocations",
    PrimitiveType.JURISDICTION: "jurisdictions",
    PrimitiveType.ESCALATION: "escalations",
    PrimitiveType.CONSEQUENCE: "consequences",
}


def _render_fact(fact: ReconciledFact) -> str:
    value = fact.selected_value
    rendered = value if isinstance(value, str) else canonical_json(value)
    return f"{fact.subject}:{fact.predicate}:{rendered}"


def _risk_for_mechanism(
    mechanism_id: str,
    primitives: tuple[ExtractedPrimitive, ...],
) -> RiskClass:
    declared = [primitive.risk_class for primitive in primitives if primitive.mechanism_id == mechanism_id]
    highest = max(declared, key=RISK_ORDER.__getitem__, default=RiskClass.UNCLASSIFIED)
    if highest is not RiskClass.UNCLASSIFIED:
        return highest
    types = {primitive.primitive_type for primitive in primitives if primitive.mechanism_id == mechanism_id}
    if types & {
        PrimitiveType.AUTHORITY,
        PrimitiveType.APPROVAL,
        PrimitiveType.REVOCATION,
        PrimitiveType.JURISDICTION,
        PrimitiveType.CONSEQUENCE,
    }:
        return RiskClass.HIGH
    return RiskClass.MODERATE if types else RiskClass.UNCLASSIFIED


def _reviewer_for(risk: RiskClass) -> str:
    if risk is RiskClass.CRITICAL:
        return "EXECUTIVE_RISK_OWNER"
    if risk is RiskClass.HIGH:
        return "DOMAIN_AND_SAFETY_REVIEWER"
    return "INSTITUTIONAL_REVIEWER"


def _source_dict(reference: SourceReference) -> dict[str, str]:
    return {
        "source_id": reference.source_id,
        "version": reference.version,
        "sha256": reference.sha256,
        "locator": reference.locator,
    }


def _mechanism_dict(mechanism: InstitutionalMechanism) -> dict[str, Any]:
    return {
        "mechanism_id": mechanism.mechanism_id,
        "version": mechanism.version,
        "actors": list(mechanism.actors),
        "roles": list(mechanism.roles),
        "authority": list(mechanism.authority),
        "policies": list(mechanism.policies),
        "evidence_requirements": list(mechanism.evidence_requirements),
        "resources": list(mechanism.resources),
        "workflow_steps": list(mechanism.workflow_steps),
        "approvals": list(mechanism.approvals),
        "deadlines": list(mechanism.deadlines),
        "revocations": list(mechanism.revocations),
        "jurisdictions": list(mechanism.jurisdictions),
        "escalations": list(mechanism.escalations),
        "consequences": list(mechanism.consequences),
        "source_references": [_source_dict(reference) for reference in mechanism.source_references],
        "risk_class": mechanism.risk_class,
        "approved": mechanism.approved,
        "metadata": mechanism.metadata,
    }


def _fact_dict(fact: ReconciledFact) -> dict[str, Any]:
    return {
        "primitive_type": fact.primitive_type.value,
        "subject": fact.subject,
        "predicate": fact.predicate,
        "selected_value": fact.selected_value,
        "agreement_state": fact.agreement_state,
        "observed_layers": [layer.value for layer in fact.layers],
        "confidence": fact.confidence,
        "statement_ids": list(fact.statement_ids),
        "source_references": [_source_dict(reference) for reference in fact.source_references],
        "conflict_ids": list(fact.conflict_ids),
    }


def _conflict_dict(conflict: ConflictRecord) -> dict[str, Any]:
    row = asdict(conflict)
    row["kind"] = conflict.kind.value
    row["primitive_type"] = conflict.primitive_type.value
    row["values_by_layer"] = {
        layer: list(values) for layer, values in conflict.values_by_layer.items()
    }
    return row


def _candidate_for(
    mechanism_id: str,
    institution_version: str,
    facts: list[ReconciledFact],
    primitives: tuple[ExtractedPrimitive, ...],
    threshold: float,
) -> tuple[CompilerCandidate, dict[str, Any], tuple[str, ...]]:
    buckets: dict[str, list[str]] = defaultdict(list)
    for fact in facts:
        if fact.selected_value is not None:
            buckets[IR_FIELDS[fact.primitive_type]].append(_render_fact(fact))
    references = {
        (reference.source_id, reference.version): reference
        for fact in facts for reference in fact.source_references
    }
    risk = _risk_for_mechanism(mechanism_id, primitives)
    confidence = round(fmean(fact.confidence for fact in facts), 6)
    conflict_ids = tuple(sorted({identifier for fact in facts for identifier in fact.conflict_ids}))
    observed_layers = tuple(
        layer for layer in (TruthLayer.NORMATIVE, TruthLayer.OPERATIONAL, TruthLayer.BEHAVIORAL)
        if any(layer in fact.layers for fact in facts)
    )
    mechanism = InstitutionalMechanism(
        mechanism_id=mechanism_id,
        version=institution_version,
        actors=tuple(sorted(set(buckets["actors"]))),
        roles=tuple(sorted(set(buckets["roles"]))),
        authority=tuple(sorted(set(buckets["authority"]))),
        policies=tuple(sorted(set(buckets["policies"]))),
        evidence_requirements=tuple(sorted(set(buckets["evidence_requirements"]))),
        resources=tuple(sorted(set(buckets["resources"]))),
        workflow_steps=tuple(sorted(set(buckets["workflow_steps"]))),
        approvals=tuple(sorted(set(buckets["approvals"]))),
        deadlines=tuple(sorted(set(buckets["deadlines"]))),
        revocations=tuple(sorted(set(buckets["revocations"]))),
        jurisdictions=tuple(sorted(set(buckets["jurisdictions"]))),
        escalations=tuple(sorted(set(buckets["escalations"]))),
        consequences=tuple(sorted(set(buckets["consequences"]))),
        source_references=tuple(references[key] for key in sorted(references)),
        risk_class=risk.value,
        approved=False,
        metadata={
            "fact_count": len(facts),
            "conflict_count": len(conflict_ids),
            "compiler_version": COMPILER_VERSION,
        },
    )
    failed_checks: list[str] = []
    if TruthLayer.NORMATIVE not in observed_layers:
        failed_checks.append("NORMATIVE_SOURCE_MISSING")
    if conflict_ids:
        failed_checks.append("CONFLICTS_REQUIRE_RESOLUTION")
    if confidence < threshold:
        failed_checks.append("CONFIDENCE_BELOW_REVIEW_THRESHOLD")
    if risk in {RiskClass.HIGH, RiskClass.CRITICAL}:
        failed_checks.append("HIGH_RISK_REVIEW_MANDATORY")
    if any(fact.selected_value is None for fact in facts):
        failed_checks.append("UNRESOLVED_FACT_VALUE")
    identity = {
        "mechanism_id": mechanism_id,
        "version": institution_version,
        "facts": [_fact_dict(fact) for fact in facts],
    }
    candidate = CompilerCandidate(
        candidate_id="candidate-" + sha256_json(identity).split(":", 1)[1][:20],
        mechanism=mechanism,
        sources=mechanism.source_references,
        observed_layers=observed_layers,
        confidence=confidence,
        conflicts=conflict_ids,
        required_reviewer_role=_reviewer_for(risk),
        qualification_checks=tuple(failed_checks),
        review_threshold=threshold,
        binding_authority=False,
    )
    row = {
        "candidate_id": candidate.candidate_id,
        "mechanism": _mechanism_dict(candidate.mechanism),
        "facts": [_fact_dict(fact) for fact in facts],
        "observed_layers": [layer.value for layer in candidate.observed_layers],
        "confidence": candidate.confidence,
        "conflict_ids": list(candidate.conflicts),
        "focused_review_required": bool(failed_checks),
        "promotion_review_required": True,
        "required_reviewer_role": candidate.required_reviewer_role,
        "failed_checks": failed_checks,
        "binding_authority": False,
    }
    return candidate, row, tuple(failed_checks)


def compile_institution(path: Path) -> dict[str, Any]:
    """Compile source evidence into non-authoritative Institutional IR candidates."""

    compiler_input = load_compiler_input(path)
    primitives = extract_all(compiler_input.sources)
    facts, conflicts = reconcile(primitives, compiler_input.settings)
    facts_by_mechanism: dict[str, list[ReconciledFact]] = defaultdict(list)
    for fact in facts:
        facts_by_mechanism[fact.mechanism_id].append(fact)

    candidate_objects: list[CompilerCandidate] = []
    candidate_rows: list[dict[str, Any]] = []
    review_queue: list[dict[str, Any]] = []
    for mechanism_id in sorted(facts_by_mechanism):
        candidate, row, failed_checks = _candidate_for(
            mechanism_id,
            compiler_input.institution_version,
            facts_by_mechanism[mechanism_id],
            primitives,
            compiler_input.settings.minimum_review_confidence,
        )
        candidate_objects.append(candidate)
        candidate_rows.append(row)
        if failed_checks:
            review_queue.append({
                "candidate_id": candidate.candidate_id,
                "mechanism_id": mechanism_id,
                "reviewer_role": candidate.required_reviewer_role,
                "reasons": list(failed_checks),
                "conflict_ids": list(candidate.conflicts),
                "status": "PENDING_AUTHORIZED_REVIEW",
            })

    conflict_rows = [_conflict_dict(conflict) for conflict in conflicts]
    qualification_checks = {
        "sources_present": bool(compiler_input.sources),
        "source_hashes_valid": all(source.reference.sha256.startswith("sha256:") for source in compiler_input.sources),
        "primitives_extracted": bool(primitives),
        "candidates_emitted": bool(candidate_rows),
        "all_candidates_unapproved": all(not candidate.mechanism.approved for candidate in candidate_objects),
        "binding_authority_false": all(not candidate.binding_authority for candidate in candidate_objects),
        "conflicts_preserved": all(
            conflict.conflict_id in {identifier for candidate in candidate_objects for identifier in candidate.conflicts}
            for conflict in conflicts
        ),
        "focused_review_items_routed": all(
            not row["focused_review_required"]
            or row["candidate_id"] in {item["candidate_id"] for item in review_queue}
            for row in candidate_rows
        ),
    }
    result_core = {
        "schema_version": "edon-institution-compiler-output.v1",
        "compiler_version": COMPILER_VERSION,
        "compiler_run_id": compiler_input.compiler_run_id,
        "institution_id": compiler_input.institution_id,
        "institution_version": compiler_input.institution_version,
        "source_manifest": [
            {
                **_source_dict(source.reference),
                "truth_layer": source.truth_layer.value,
                "kind": source.kind,
                "format": source.source_format.value,
            }
            for source in compiler_input.sources
        ],
        "extraction_summary": {
            "source_count": len(compiler_input.sources),
            "primitive_count": len(primitives),
            "mechanism_count": len(candidate_rows),
            "conflict_count": len(conflict_rows),
            "focused_review_count": len(review_queue),
        },
        "candidates": candidate_rows,
        "conflicts": conflict_rows,
        "review_queue": review_queue,
        "qualification": {
            "checks": qualification_checks,
            "passed": all(qualification_checks.values()),
            "status": "COMPILER_OUTPUT_QUALIFIED" if all(qualification_checks.values()) else "COMPILER_OUTPUT_REJECTED",
        },
        "binding_authority": False,
        "claim_boundary": (
            "Deterministic compilation of explicitly structured or EDON-annotated sources into "
            "unapproved candidate IR; not validated natural-document extraction or deployment authority."
        ),
    }
    result_core["compiler_manifest"] = {
        "input_sha256": sha256_json(compiler_input.raw_input),
        "compiled_payload_sha256": sha256_json(result_core),
        "deterministic": True,
    }
    return result_core


def compile_to_file(input_path: Path, output_path: Path) -> dict[str, Any]:
    result = compile_institution(input_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return result


__all__ = ["CompilerInputError", "compile_institution", "compile_to_file"]