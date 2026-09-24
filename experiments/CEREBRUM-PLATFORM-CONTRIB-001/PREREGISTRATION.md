# Frozen Qwen contribution preregistration

Frozen: 2026-08-23, before any Qwen adapter for this experiment was trained.

- Base model, seeds, counts, target instrument and hyperparameters are fixed in
  `configs/qwen3-4b-platform-contribution.json`.
- Training data may not be regenerated after Qwen training begins.
- Protected inputs and labels may not enter either training condition.
- All four prediction files must be frozen by content hash before labels are opened.
- `score_qwen.py` permits one protected score receipt.
- Both Platform 002 seeds must pass every advancement threshold.
- A proxy pass does not alter Qwen thresholds and cannot be reported as Cerebrum evidence.
- The proxy target may be used only for Qwen development rehearsal after its
  labels are opened; confirmatory evaluation requires a fresh custodian-held target.
- A failed Qwen gate is preserved as a negative result.