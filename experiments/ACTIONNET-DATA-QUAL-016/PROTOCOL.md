# Protocol

- Training: 368 fresh records, including 96 transitions, 96 queue traces, 48
  pair contrasts, 64 certificates, 32 queue-order, and 32 queue-partition
  records.
- Safety focus: 16 fresh delayed-evidence pairs with balanced ALLOW and ABSTAIN
  certificates; delayed interventions receive the highest training weight.
- Development selection: 64 fresh records, 16 per scored task.
- Untouched confirmation: 192 fresh records, 48 per scored task.
- Families: training 820--823, development 840--841, confirmation 860--863.
- Development and confirmation use separate held-out renderers.
- DEV-014 and DEV-015 validation cases and pairs are excluded from training.
- Confirmation remains sealed unless a checkpoint passes all 26 frozen checks.