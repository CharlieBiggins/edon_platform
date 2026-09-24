# Protocol

- Parent motivation: frozen `CEREBRUM-DEV-009-RB1` negative result.
- Training profiles: `CLOCK_GRID` and `CONTROL_SHEET`.
- Training renderers: `DECISION_CLOCK_GRID`, `MULTI_SYSTEM_JOURNAL`,
  `STATE_DELTA_PACKET`, and `QUEUE_CONTROL_SHEET`.
- Held-out profile and renderer: `REGISTER` / `CROSS_FORMAT_REGISTER`.
- Training semantic families: 400--406 and 420--426.
- Validation semantic families: 440--443.
- Training pairs: 336; validation pairs: 48.
- Training records: 4,032, balanced across six task types.
- Validation records: 192, 48 each for certificate, transition, queue trace,
  and pair contrast.
- Every queue target must contain every submitted event exactly once in the
  canonical order. Executed and deferred lists must be disjoint, exhaustive,
  and order-preserving subsequences.
- Resolved and unresolved appeal timing remains determined only by events at or
  before the stated decision clock.

No RB1 case, prompt, source, institution, generator, renderer, or semantic
family may be reused. The exposed RB1 validation remains audit-only.
