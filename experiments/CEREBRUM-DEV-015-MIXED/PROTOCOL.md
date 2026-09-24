# Protocol

- Parent: frozen DEV-013 `continuation-step-6` adapter.
- Seed: `26090542`.
- Training: 384 mixed replay records; 24 optimizer steps; effective batch 16;
  learning rate `3e-6`; checkpoints at steps 12 and 24.
- Development: 64 fresh cases, 16 per scored task, for checkpoints 12 and 24.
- Eligibility: all 26 inherited full-regression checks must pass.
- Ranking among eligible checkpoints: queue exactness, transition exactness,
  certificate decisions, unresolved appeals, pair exactness, then earlier
  step.
- Confirmation: 192 fresh single-use cases, 48 per scored task, opened only
  after a development pass.
- Transfer authorization remains false regardless of outcome.