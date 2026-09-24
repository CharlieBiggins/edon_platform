# Protocol

- Source: compute-bounded subset of `ACTIONNET-DATA-QUAL-009`.
- Base: `Qwen/Qwen3-4B-Instruct-2507`, revision
  `cdbee75f17c01a7cc42f958dc650907174af0554`.
- Seeds: `26082491` and `26082492`.
- Training: 2,688 records per seed, one epoch, effective batch 16, 168
  optimizer steps.
- Training profiles: LEDGER and MATRIX.
- Development validation: 192 held-out GRAPH-profile records, 48 each for
  certificate, transition, queue trace, and pair contrast.
- Prediction: deterministic decoding, deterministic compilation, per-case
  checkpointing, and one common frozen validation hash.
- Gate: every seed must pass all 23 registered schema, accuracy, execution,
  safety, and generation checks; both seeds must then pass the six-check
  reproducibility summary.

The registered success disposition was
`COMPUTE_BOUNDED_SYNTHETIC_TRANSFER_REPRODUCED`. The observed disposition is
`RB1_TRANSFER_NOT_ESTABLISHED` and is immutable under this identity.
