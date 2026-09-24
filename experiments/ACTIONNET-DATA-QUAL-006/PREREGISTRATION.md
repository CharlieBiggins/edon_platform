# ACTIONNET-DATA-QUAL-006 preregistration

Protocol identity: `ACTIONNET-DATA-QUAL-006`  
Frozen: 2026-08-14, after DEV-004 scoring and before any DEV-006 training.

## Motivation

DEV-004 seed 26081242 failed only the pivotal-mechanism certificate floor. Its
three `UNRESOLVED_APPEAL` base certificates were expected `ALLOW` after an
appeal resolved before disposition, but were predicted `CONTESTED`. Pair
contrast, queue, transition, schema, and safety behavior remained strong.

## Additive design

- Parent: `ACTIONNET-DATA-QUAL-005-result-v1.0.0`.
- Training families: 110--125; validation families: 140--147.
- Training renderers: `CONTROL_BRIEF`, `TIMELINE_LEDGER`, `PROCESS_PACKET`.
- Held-out renderer: `REVIEW_MEMORANDUM`.
- Training: 384 pairs, 768 trajectories, 8,064 records.
- Validation: 192 pairs, 384 trajectories, 1,344 records.
- At least 400 appeal-focused training certificates and 60 validation
  certificates.
- Validation appeal certificates must balance resolved `ALLOW` and unresolved
  `CONTESTED` cases exactly.
- Appeal resolution times span 6, 8, 9, 11, 12, and 14 around disposition time
  10.

All case IDs, prompts, source, institution, generator, authority-graph,
workflow-graph, family, domain, renderer, and seed lineages must be disjoint from
ActionNet-005. DEV-004 validation cases are prohibited from training.

## Qualification

Every registered control must pass, including independent engine/scheduler
agreement, exact pivotality, observability, label isolation, lineage separation,
appeal hard-negative balance, timing diversity, decision-weight balance, and
zero predecessor prompt/case overlap.

Future-public, protected, and real-institution families remain unmaterialized.