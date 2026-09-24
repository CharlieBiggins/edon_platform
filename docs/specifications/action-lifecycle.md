# Action Lifecycle

Status: `CANONICAL_SPECIFICATION_V1_NOT_FULLY_IMPLEMENTED`

The Action Lifecycle separates model proposals, human approval evidence, Kernel
authorization, and operational execution.

Machine-readable contracts:

- `schemas/actions/action-proposal.schema.json`;
- `schemas/actions/authorization-decision.schema.json`;
- `schemas/actions/execution-request.schema.json`; and
- `schemas/actions/execution-record.schema.json`.

## Lifecycle

```text
PROPOSED
→ EVALUATED
→ APPROVAL_REQUIRED when applicable
→ KERNEL_REEVALUATION
→ AUTHORIZED or DENIED
→ RESERVED
→ DISPATCHED
→ ACKNOWLEDGED
→ PARTIAL
→ VERIFIED
→ COMPLETED, FAILED, CANCELLED, or COMPENSATED
```

Kernel may also return `ABSTAIN`, `ESCALATE`, `REVISE`, or `REASSIGN`. Those
results return to the Control Plane and do not enter execution.

## Proposal contract

A proposal binds the exact action, expected consequences, evidence,
uncertainty, preconditions, resource needs, state version, policy and IR
versions, model or solver lineage, required authority, reversibility, and
expiry. It always remains non-binding.

## Authorization contract

An authorization decision binds an unchanged proposal hash, expected state,
policy and authority versions, evidence set, evaluated constraints, decision,
scope, issue time, expiry, Kernel identity, and signature. Only the independent
Kernel service may issue this record.

## Execution contract

An execution request references an existing proposal and authorization; it
cannot carry free-form replacement action content. Execution Assurance verifies:

- authorization is valid, signed, unexpired, and unused outside its scope;
- the proposal and relevant state have not changed;
- preconditions, evidence freshness, approvals, reservations, and risk limits
  still hold;
- the connector and action schema are approved;
- the idempotency key has not already completed.

Failed validation leaves institutional state unchanged. Partial effects are
recorded explicitly and invoke a registered retry, cancellation, human-takeover,
or compensation procedure.

## Invariants

1. No model output directly executes an action.
2. No public caller can declare an action authorized.
3. Human approval cannot bypass Kernel reevaluation.
4. Authorization and execution have independent custody and audit records.
5. Every consequential effect can be traced to proposal, policy, authority,
   connector, receipt, and outcome evidence.