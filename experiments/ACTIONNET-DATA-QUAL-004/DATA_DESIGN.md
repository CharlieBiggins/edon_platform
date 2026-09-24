# ACTIONNET-DATA-QUAL-004 Data Design

## Core representation

Each trajectory separates institutional state from the submitted event queue.

The state contains:

- a request, disposition time, scope, and source/target institutions;
- requester, delegator, approver, and reviewer actors;
- delegated authority validity, scope, rank, and revocation state;
- evidence status, provenance, arrival time, and expiry;
- required and collected workflow approvals;
- appeal state;
- resource capacity, prior reservations, and demand;
- routing acceptance and jurisdiction compatibility;
- policy version/effectivity; and
- conflict and request-format state.

Every event exposes:

- opaque event and actor identifiers;
- logical time;
- priority;
- deterministic sequence number;
- operation;
- typed target; and
- typed operand.

Opaque identifiers carry no answer labels.

## Execution semantics

Submitted order is not authoritative. The two reference engines independently construct the canonical order using `(time, priority, sequence, event_id)`.

Events at or before disposition time execute. Later events are deferred. The execution receipt records canonical order, executed events, deferred events, intermediate semantic states, and the final state hash.

The model remains advisory. Every certificate contains `binding_authority: false`.

## Learning tasks

### Certificate

Apply the queue and emit the canonical non-authoritative institutional certificate.

### Transition

Return the typed post-state, changed fields, final semantics, decision, failed conditions, and execution receipt.

### Queue trace

Return canonical ordering, execution/deferment, per-event semantic states, and the final state hash.

### Pair contrast

Execute both queues and identify whether the disposition changes, both certificates, event differences, and post-state differences.

## Renderer policy

Training uses three semantically equivalent surfaces:

- FORMAL: canonical structured JSON;
- EVENT_STREAM: line-oriented operational events;
- OPERATIONS_MEMO: prose with embedded typed state and event entries.

Repair validation uses CASE_DOCKET, which is excluded from training. Splits are created before rendering, preventing alternate views of one trajectory from crossing the boundary.

## Balance and coverage

The pair schedule is four pivotal, one invariance, and one contextual pair per six pairs. All twelve pivotal mechanisms cycle independently of institution identity. Training loss weights balance decision classes, and pivotal pair rows receive additional weight.

Qualification reports microscopic correctness and aggregate decision-distribution hashes. Aggregate hashes are reproducibility receipts, not evidence of real-world population fidelity.