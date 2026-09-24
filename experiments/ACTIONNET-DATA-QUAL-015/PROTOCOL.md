# Protocol

- Training: 384 replay records, including 96 transitions, 96 queue traces, 64
  pair contrasts, 64 certificates, 32 queue-order, and 32 queue-partition
  records.
- Development selection: 64 fresh records, 16 per scored task.
- Untouched confirmation: 192 fresh records, 48 per scored task.
- Development families: 784--785; confirmation families: 800--803.
- Development and confirmation use different held-out renderers.
- DEV-014 cases, pairs, semantic families, and renderer are disjoint.
- Confirmation remains unopened unless a development checkpoint passes the
  complete safety and retention gate.