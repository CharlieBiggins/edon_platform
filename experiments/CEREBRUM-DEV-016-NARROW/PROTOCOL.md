# Protocol

- Parent: frozen DEV-015 `continuation-step-12` adapter. Both DEV-015
  checkpoints had identical aggregate metrics; the earlier checkpoint limits
  further drift.
- Parent audit: compare both 64-case development prediction files at field
  level without reading the sealed DEV-015 confirmation.
- Seed: `26090612`.
- Training: 368 fresh narrow-repair records; 12 optimizer steps; effective
  batch 16; learning rate `1e-6`; checkpoints at steps 6 and 12.
- Development: 64 fresh cases, 16 per scored task, for both checkpoints.
- Eligibility: all 26 inherited full-regression checks must pass.
- Ranking among eligible checkpoints: transition post-state, pivotal
  certificate behavior, queue exactness, transition exactness, pair exactness,
  then earlier step.
- Confirmation: a new 192-case single-use split, opened only after a complete
  development pass.
- Transfer authorization remains false regardless of outcome.