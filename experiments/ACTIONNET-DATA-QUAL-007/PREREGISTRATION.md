# ACTIONNET-DATA-QUAL-007 preregistration

Protocol: `ACTIONNET-DATA-QUAL-007-v1.0.0`  
Frozen: August 16, 2026, after Transfer-006 scoring and before DEV-007 training.

## Registered design

- Parent semantics: `ACTIONNET-DATA-QUAL-006-result-v1.0.0`.
- Fresh training families: 180--203; validation families: 220--227.
- Future public families 240--247 and protected families 250--257 remain
  unmaterialized.
- Training renderers: `DECISION_CLOCK_GRID`, `MULTI_SYSTEM_JOURNAL`,
  `STATE_DELTA_PACKET`, and `QUEUE_CONTROL_SHEET`.
- Held-out renderer: `CROSS_FORMAT_REGISTER`.
- Four tasks: certificate, transition, queue trace, and pair contrast.
- Every trajectory must contain both executed and deferred events.
- Decision clocks must cover 8, 9, 10, 11, and 12 in both splits.
- Every final state must differ from its initial state on at least two paths.
- Queue supervision is weighted above transition supervision, which is weighted
  above certificate supervision; pivotal pair diffs are separately upweighted.

All independent-engine, lineage separation, prompt hygiene, deterministic
generation, and non-authority controls must pass. No exposed Transfer-006 case
may enter the corpus.