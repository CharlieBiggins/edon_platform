# Protocol

- Training parent: frozen DEV-015 continuation-step-12, adapter SHA-256
  2dd862942bfd21508c18f46cd1d9a67fe5da0e4ef7792860bcd8968ecce8be1a.
- Scientific predecessor: DEV-016, frozen at 23/26 checks for both candidates,
  12 shared failures, one delayed-evidence unsafe authorization, and sealed
  confirmation.
- Seed: 26090642.
- Training: 384 fresh records, effective batch 16, 24 optimizer steps,
  learning rate 1e-6, one complete seeded permutation without replacement.
- Checkpoints: steps 12 and 24. Step 24 is the registered full-exposure
  candidate; step 12 is an intermediate diagnostic.
- Development: 64 fresh cases, 16 per scored task, for both checkpoints.
- Eligibility: every one of the inherited 26 full-regression checks must pass.
- Ranking among eligible candidates: zero unsafe authorizations, transition
  post-state, pivotal certificates, queue exactness, transition exactness,
  pair exactness, then earlier step.
- Confirmation: 192 new single-use cases, opened only after a development
  candidate passes all 26 checks.
- Transfer and seed-reproducibility authorization remain false.
