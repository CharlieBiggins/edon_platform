# Protocol

- Dataset: `ACTIONNET-DATA-QUAL-010`.
- Base: `Qwen/Qwen3-4B-Instruct-2507`, frozen revision
  `cdbee75f17c01a7cc42f958dc650907174af0554`.
- Seeds: `26090401` and `26090402`.
- Training: 4,032 records, one epoch, effective batch 16, 252 expected L4
  optimizer steps.
- Training tasks: 672 each of certificate, transition, queue trace, pair
  contrast, queue order, and queue partition.
- Validation: 192 fresh REGISTER-profile records under the held-out
  `CROSS_FORMAT_REGISTER` renderer; 48 each of the four scored tasks.
- Training and inference use the same 4,096-token maximum and abort on training
  truncation.
- Prediction uses deterministic decoding, per-case checkpoints, no retries,
  and deterministic compilation of hashes from model-predicted states.
- Scoring is locked until both registered prediction freezes are complete.

## Queue integrity contract

Every submitted event identifier must occur exactly once in
`ordered_event_ids`. `executed_event_ids` and `deferred_event_ids` must be
disjoint, exhaustive, order-preserving subsequences split by whether event time
is at or before the stated decision clock.

## Advancement

Each seed must pass all 26 frozen checks, including zero unsafe authorizations,
at least 90% unresolved-appeal certificate accuracy, and explicit floors for
queue order, execution, deferral, step semantics, final state, and complete
queue exactness. Both seeds must then pass the six-check reproducibility
summary.
