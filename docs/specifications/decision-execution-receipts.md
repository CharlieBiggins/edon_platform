# Decision, Execution, and Compensation Receipts

Status: `CANONICAL_SPECIFICATION_V1_NOT_IMPLEMENTED`
Vision: `CEREBRUM-PLATFORM-VISION-002`

Receipts provide immutable, content-bound evidence of why a decision was made,
what was attempted, and what happened afterward. They are audit artifacts and
Control Graph nodes; they do not substitute for the underlying evidence.

Machine-readable contracts:

- `schemas/receipts/decision-receipt.schema.json`;
- `schemas/receipts/execution-receipt.schema.json`; and
- `schemas/receipts/compensation-record.schema.json`.

## Decision Receipt

Created for every Kernel result, including denial, abstention, approval
required, escalation, revision, and reassignment. It binds:

- exact proposal identity and hash;
- Control Graph, state, IR, policy, authority, and domain-pack versions;
- identity, capability, mandate, commitment, reservation, evidence, approval,
  jurisdiction, conflict, precondition, and risk checks;
- decision, conditions, issue time, expiry, Kernel identity, and signature.

The receipt explains the decision without exposing evidence outside authorized
compartments. A signed decision receipt cannot be edited into an authorization
for a different proposal.

## Execution Receipt

Execution Assurance appends lifecycle entries for validation, reservation,
dispatch, acknowledgement, partial effects, retries, cancellation, observed
outcomes, verification, completion, failure, and compensation. It binds the
authorization decision, connector, idempotency key, request and response
hashes, state versions, and event evidence.

`ACKNOWLEDGED` means the target accepted or recognized a request. It does not
mean the action completed. `COMPLETED` means the registered execution lifecycle
completed. It does not mean the intended outcome is verified.

## Compensation Record

The compensation record links the triggering execution, failure or partial
effect, recovery proposal, new decision receipt, recovery execution receipt,
residual effects, human review, and terminal status. Compensation never deletes
or replaces the original execution record.

## Integrity and access

Receipts use content hashes, signatures, event and trace identifiers, immutable
sequence numbers, tenant and compartment boundaries, and retention policy.
Redacted views preserve receipt identity and hash while minimizing protected
content.

## Invariants

1. Every Kernel decision produces a Decision Receipt.
2. Every execution attempt produces an Execution Receipt, including validation
   failure before dispatch.
3. Delivery, acknowledgement, completion, outcome observation, and outcome
   verification remain distinct.
4. Compensation requires a new proposal and Kernel decision.
5. Receipts cannot be rewritten to conceal failure, override, or human
   intervention.
6. Receipt existence does not prove correctness; it makes the evidence and
   responsible versions inspectable.