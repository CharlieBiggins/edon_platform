# ACTIONNET-DATA-QUAL-004 Protocol Specification

Protocol identity: `ACTIONNET-DATA-QUAL-004-v0.1.0`.

Result identity: `ACTIONNET-DATA-QUAL-004-result-v1.0.0`.

This specification was fixed before writing the frozen result artifacts. Implementation diagnostics performed during construction are developmental and are not presented as an untouched external confirmation.

## Purpose

Test whether ActionNet can generate reproducible multi-actor, multi-event institutional trajectories under deterministic scheduling while preserving the authority boundary established by earlier experiments.

The package is an additive successor to `ACTIONNET-DATA-QUAL-003-result-v1.0.0`. The active `CEREBRUM-DEV-002` experiment continues against its frozen v3 parent and must not be relabeled as a v4 result.

## Registered semantic additions

1. Every event contains a time, priority, sequence, actor, operation, target, and visible value.
2. Events execute in ascending `(time, priority, sequence, event_id)` order.
3. Events after the request disposition time are recorded as deferred and cannot alter the disposition.
4. Each trajectory contains at least four submitted events and at least four distinct actors.
5. Cross-institution cases include explicit routing and jurisdiction state.
6. Two separately implemented scheduler, transition, and evaluation paths must agree exactly.
7. Only adjacent resource-reservation deltas sharing time, priority, operation, and target may be aggregated. Aggregated and sequential execution must have identical final state and certificate.

## Registered mechanisms

- revocation propagation;
- delayed evidence;
- approval withdrawal;
- resource contention;
- policy change;
- routing rejection;
- jurisdiction shift;
- conflict assertion;
- malformed request;
- simultaneous-event priority race;
- evidence expiry;
- unresolved appeal.

Pivotal pairs must change the final decision. Invariance pairs alter actor identity and submitted queue order while preserving scheduled semantics. Contextual pairs change a subordinate resource fact under an already malformed request and must preserve the invalid disposition.

## Registered splits

Training uses semantic families 30--41, domains procurement/research/education, and FORMAL, EVENT_STREAM, and OPERATIONS_MEMO renderers.

Repair validation uses semantic families 50--53, health-administration/civic-administration domains, and the unseen CASE_DOCKET renderer.

Families 54--57 are reserved for a future public instrument. Families 58--61 are protected. Neither is materialized here.

## Registered records

- 240 training pairs, 480 training trajectories, and 5,040 training records;
- 60 repair-validation pairs, 120 repair-validation trajectories, and 420 repair-validation records;
- tasks: CERTIFICATE, TRANSITION, QUEUE_TRACE, and PAIR_CONTRAST.

Decision weights are computed only from the training split. Pivotal pair-contrast rows receive weight 2.0. Validation rows remain unweighted.

## Required qualification controls

- byte-identical deterministic regeneration;
- exact agreement between independent reference engines and schedulers;
- every pivotal pair changes and every invariance/contextual pair preserves the decision;
- all twelve pivotal mechanisms appear in training and repair validation;
- multi-step, simultaneous, deferred, multi-actor, and cross-institution coverage;
- exact safe-aggregation equivalence;
- no target/audit metadata or decision-label tokens in model-facing inputs;
- visible event operands and scheduling keys in every renderer;
- zero conflicting prompt groups;
- disjoint prompts, cases, semantic families, trajectories, pairs, institutions, sources, generators, authority graphs, and workflow graphs across splits;
- zero case or prompt reuse from ACTIONNET-DATA-QUAL-003;
- held-out renderer isolation;
- balanced effective decision weights;
- binding authority false in every supervised target;
- future public and protected families unmaterialized.

## Interpretation boundary

Passing qualifies a project-authored synthetic corpus for a separate internal EventNet development campaign. It does not prove real institutional fidelity, source grounding, human behavioral fidelity, planet-scale performance, independent authorship, autonomous authority, or production safety.