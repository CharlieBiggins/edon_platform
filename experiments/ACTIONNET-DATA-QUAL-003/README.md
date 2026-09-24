# ACTIONNET-DATA-QUAL-003

Status: `READY_FOR_CEREBRUM_REPAIR_TRAINING`.

Frozen result: `ACTIONNET-DATA-QUAL-003-result-v1.0.0`.

This additive successor is the registered response to `CEREBRUM-DEV-001-run-2026-08-09-v1.0.0`. It does not modify `ACTIONNET-DATA-QUAL-002` and does not copy the 120 exposed development cases into training.

The repair target is event-sensitive, cross-renderer learning. The first Cerebrum adapter learned valid certificate structure and benefited materially from counterfactual records, but it incorrectly authorized 17 pivotal event-log interventions. This successor specifies new-lineage, multi-view trajectories and explicit event-to-post-state supervision before another GPU candidate may be trained.

The frozen result contains 3,600 training records, 300 repair-validation records, and 600 canonical trajectories. Formal, event-log, and memo views are used for training; a new ledger renderer and semantic families 20--23 are held out for repair validation. Certificate, transition, and pair-contrast tasks are present. All 23 controls pass, including zero exposed-development overlap, zero prompt conflicts, visible event operands, disjoint lineages, balanced effective decision weights, and unmaterialized public/protected families.

Run:

```bash
python run_campaign.py
python -m unittest discover -s tests -v
sha256sum -c results/checksums.sha256
```

See `PREREGISTRATION.md`, `DATA_DESIGN.md`, and `CEREBRUM_REPAIR_HANDOFF.md`.