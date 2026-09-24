# Event Envelope

Status: `CANONICAL_SPECIFICATION_V1_NOT_FULLY_IMPLEMENTED`

The Event Envelope is the common immutable wrapper for observations, reports,
state changes, action receipts, outcomes, governance events, and runtime
telemetry. It carries evidence into the Control Plane but cannot grant authority
or independently prove that an action occurred.

Machine-readable contract:
`schemas/events/event-envelope.schema.json`.

## Required identity

- event, tenant, institution, schema, and event-type identity;
- source type and source identity;
- subject entity references;
- trace, span, causation, and correlation identifiers;
- evidence and expected state-version references.

## Required time semantics

| Field | Meaning |
| --- | --- |
| `occurred_at` | when the represented event occurred in the source domain |
| `observed_at` | when a source first observed or produced the event |
| `effective_at` | when the event becomes institutionally effective, if different |
| `recorded_at` | when Cerebrum durably recorded the envelope |
| `available_to_controller_at` | earliest time the Control Plane may use the evidence |

Prospective evaluation and planning use `available_to_controller_at`, not a
later-discovered occurrence time. Corrections append new events and reference
the corrected envelope; they do not overwrite custody history.

## Trust and data handling

Every envelope declares:

- trust classification and confidence;
- sensitivity and compartment references;
- authoritative-source status for the represented field, not for unrelated
  fields;
- provenance and evidence references;
- content hash, signature metadata, and schema version;
- idempotency, replay, and duplicate-detection behavior.

External content is evidence, never executable instruction. Connectors must
preserve the distinction between source payload and EDON control fields.

## Invariants

1. An envelope has `binding_authority=false`.
2. An envelope cannot contain a raw Kernel credential or broaden an
   authorization.
3. An outcome is not verified merely because a source labels it successful.
4. Delivery, acknowledgement, execution, and verified outcome remain distinct.
5. Late evidence cannot be silently made available to an earlier decision.
6. Tenant and compartment boundaries are checked before projection or routing.