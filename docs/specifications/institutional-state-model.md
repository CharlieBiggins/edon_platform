# Institutional State Model

Status: `CANONICAL_SPECIFICATION_V1_NOT_FULLY_IMPLEMENTED`

The Institutional State Model separates what is believed, what is authorized,
what has executed, and what outcome has been established. These dimensions may
be related, but no dimension silently promotes another.

Machine-readable contract:
`schemas/institution/institutional-state.schema.json`.

## State dimensions

### Epistemic

`REPORTED`, `OBSERVED`, `INFERRED`, `DISPUTED`, `VERIFIED`, or `UNKNOWN`.

This dimension records the evidentiary status of a proposition. `INFERRED`
requires model or derivation lineage. `VERIFIED` requires an identified
verification method and evidence.

### Authority

`UNASSESSED`, `PROPOSED`, `APPROVAL_REQUIRED`, `AUTHORIZED`, `DENIED`,
`EXPIRED`, or `REVOKED`.

Human approval may satisfy a policy condition, but the state becomes
`AUTHORIZED` only through a current Kernel decision.

### Execution

`NOT_STARTED`, `RESERVED`, `DISPATCHED`, `ACKNOWLEDGED`, `PARTIAL`,
`COMPLETED`, `FAILED`, `CANCELLED`, or `COMPENSATED`.

Execution state is derived from Execution Assurance and connector receipts. It
does not establish that the intended outcome occurred.

### Outcome

`UNKNOWN`, `REPORTED`, `OBSERVED`, `VERIFIED`, `CONTESTED`, or `FAILED`.

Outcomes return through the Observation and Connector Gateway and update the
Control Plane before later reasoning may treat them as current state.

## Additional requirements

Each state assertion or snapshot records ownership, source precedence,
effective and recorded time, controller availability, entity resolution,
conflicts, compartment visibility, provenance, and version history. Conflicting
latest assertions are surfaced rather than resolved by arbitrary write order.

## Compatibility

The existing five-view Cerebrum state contracts remain v1 reference contracts.
They must not be rewritten in place. Implementations migrate to this
multidimensional model through explicit adapters and tests.

## Invariants

1. Model-predicted state and executor-computed state are reported separately.
2. Authorization does not imply dispatch or outcome.
3. Dispatch does not imply completion.
4. Completion does not imply a verified beneficial outcome.
5. Disputed facts remain visible to permitted reviewers.
6. State updates are versioned, replayable, tenant isolated, and auditable.