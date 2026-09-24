# Institution Compiler

The controlling platform vision governs compiler output through the canonical
Institutional IR lifecycle: draft, validation, review, approval, activation,
amendment, supersession, migration, and retirement. Existing compiler output
remains candidate IR and is not automatically active policy.

The Institution Compiler converts heterogeneous institutional sources into
provenance-linked candidate mechanisms for authorized review.

## Implemented MVP

The executable compiler under `src/edon/compiler/` currently provides:

- inline or bundle-relative source ingestion with SHA-256 verification;
- structured JSON and deterministic `EDON|...` annotated-text extraction;
- thirteen typed institutional primitives;
- normative, operational, and behavioral reconciliation;
- explicit normative conflicts, cross-layer mismatches, and missing-normative
  records;
- risk and confidence-based focused review routing;
- unapproved Institutional IR candidates, source lineage, qualification checks,
  and a deterministic output manifest;
- a CLI and a synthetic end-to-end example.

```bash
PYTHONPATH=src python -m edon.cli compile-institution \
  examples/hospital/compiler-input.json \
  --output examples/hospital/compiler-output.json
```

## Inputs

- policies, regulations, SOPs, contracts, and guidance;
- organization charts, delegations, IAM, role definitions, and approval matrices;
- workflow systems, APIs, configuration, tickets, and audit records;
- behavioral traces and operator decisions.

## Three truth layers

| Layer | Meaning | Authority |
| --- | --- | --- |
| Normative | What authorized sources require | Presumptive rule source |
| Operational | What deployed systems permit or enforce | Implementation evidence |
| Behavioral | What people and systems actually do | Descriptive evidence only |

Agreement raises confidence. Conflict is preserved as a first-class review item;
it is never resolved by majority vote or by silently treating behavior as policy.

## Compiler output

Each candidate mechanism includes:

- typed IR fragment;
- source spans and hashes;
- extraction method and confidence;
- normative/operational/behavioral agreement status;
- ambiguity and conflict records;
- risk class and required reviewer role;
- approval, rejection, or revision history.

All emitted candidates set `approved=false` and `binding_authority=false`.
Low-risk candidates that agree across layers can avoid the focused exception
queue, but they still require an authorized promotion decision.

## Source formats

`STRUCTURED_JSON` sources contain a `statements` array. Every statement declares
`mechanism_id`, `primitive_type`, `subject`, `predicate`, and `value`, with
optional extraction confidence and risk class.

`EDON_ANNOTATED_TEXT` sources use one deterministic record per line:

```text
EDON|mechanism|primitive_type|subject|predicate|value|confidence|risk_class
```

This annotation format is an ingestion boundary for extractors and connectors;
it is not evidence that arbitrary PDFs, policies, logs, or enterprise systems can
already be compiled correctly without human or model-assisted preprocessing.

## Promotion rule

Automation may propose. Only an authorized review can promote a candidate into a
live institutional model. High-impact mechanisms require review regardless of
model confidence.

## Not yet implemented

- general natural-document extraction and OCR;
- live IAM, EHR, ERP, ticketing, or audit-log connectors;
- source authority discovery and legal validity adjudication;
- signed approval workflow and production registry promotion;
- real-institution accuracy, security, privacy, and operational validation.