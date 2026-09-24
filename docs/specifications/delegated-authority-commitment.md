# Delegated Authority and Commitment Layer

Status: `CANONICAL_SPECIFICATION_V1_NOT_IMPLEMENTED`
Vision: `CEREBRUM-PLATFORM-VISION-002`

This layer governs who may bind the institution, what the institution has
promised, and which resources are available for an exact proposal. Its records
are represented in the Institutional Control Graph while dedicated services
own their lifecycle and validation.

Machine-readable contracts:

- `schemas/authority/identity-capability.schema.json`;
- `schemas/authority/mandate.schema.json`;
- `schemas/authority/commitment.schema.json`; and
- `schemas/authority/resource-reservation.schema.json`.

## Identity and Capability Registry

Records human, service, agent, robot, system, and organization identity;
credentials; roles; capabilities; operating status; scope; preconditions; and
reliability. Capability means an actor can potentially perform an action. It
does not mean the actor may perform it.

## Mandate Service

A mandate is a signed, scoped, time-bound, revocable delegation from an
accountable principal under active policy. It binds:

- grantor, grantee, action classes, targets, jurisdictions, and purpose;
- quantitative, temporal, risk, spending, and resource limits;
- required approvals, separation of duties, and escalation rules;
- policy and authority versions, effective time, expiry, revocation, and
  delegation depth;
- provenance, signature, and audit lineage.

Human approval may create approval evidence or a mandate within the approver's
own authority. The Kernel must reevaluate the exact proposal afterward.

## Commitment Ledger

A commitment records a promise or obligation with issuer, beneficiary, owner,
deliverable, due time, conditions, dependencies, priority, breach rules,
status, evidence, and discharge or compensation. Commitments are versioned and
append-only. Amendment, transfer, waiver, breach, and discharge require
authorized lifecycle transitions.

## Resource Reservation System

A reservation binds an exact resource or capacity amount, proposal or plan,
owner, priority, effective interval, expiry, conflict policy, and release or
consumption state. Reservations prevent double allocation but do not authorize
the action that consumes the resource.

## Compensation Manager

Compensation handles partial or failed execution through registered recovery
plans. Every consequential compensating action becomes a new proposal and
requires current mandate, policy, evidence, resource, and Kernel checks. A
previous authorization cannot be stretched to cover a different recovery
action.

## Invariants

1. Identity is not capability; capability is not mandate; mandate is not a
   Kernel decision; authorization is not execution.
2. Expired, revoked, exceeded, or out-of-scope mandates fail closed.
3. A mandate cannot delegate more authority than its grantor possesses.
4. Commitments and reservations remain visible to planning and Kernel checks.
5. Resource reservation does not establish successful delivery or outcome.
6. Compensation preserves the original failure and receipt chain.