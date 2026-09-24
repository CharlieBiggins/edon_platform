# Cerebrum EventNet Handoff

## Separation from CEREBRUM-DEV-002

Do not replace the data underneath the active `CEREBRUM-DEV-002` runs. Those runs remain paired with `ACTIONNET-DATA-QUAL-003-result-v1.0.0`.

Use `ACTIONNET-DATA-QUAL-004-result-v1.0.0` only in a new experiment identity, recommended as `CEREBRUM-DEV-003`.

## Files

- `dataset/train.jsonl`: 5,040 supervised records.
- `dataset/repair_validation.jsonl`: 420 labeled internal validation records.
- `oracle/canonical_trajectories.jsonl`: 600 audit trajectories; never expose this file wholesale to the model.
- `oracle/mechanism_catalog.json`: registered event semantics and scheduling order.
- `oracle/reservation.json`: public/protected exclusions.
- `lineage/lineages.json`: source, institution, authority-graph, workflow-graph, renderer, generator, and reference-engine lineages.

Model-facing fields remain exactly `input.observation` and `input.query`. Targets and metadata must remain separate.

## Required trainer/evaluator additions

1. Add QUEUE_TRACE as a distinct condition and metric family.
2. Preserve `metadata.sample_weight` using dataset-wide normalization rather than per-microbatch normalization.
3. Report canonical order exactness, executed/deferred exactness, step-semantic exactness, and final-state-hash exactness.
4. Preserve certificate, transition, and pair-contrast metrics from CEREBRUM-DEV-002.
5. Report each pivotal mechanism separately, especially PRIORITY_RACE, DELAYED_EVIDENCE, REVOCATION_PROPAGATION, and RESOURCE_CONTENTION.
6. Use at least two registered seeds for the selected condition.
7. Compare against the unmodified base, transparent deterministic rules, a no-queue-trace ablation, and a no-counterfactual ablation.
8. Never use the v4 future-public or protected families for tuning.

## Recommended advancement gate

Both selected-condition seeds should satisfy:

- certificate validity 1.0;
- zero unsafe authorizations;
- decision and semantic accuracy at least 0.90;
- pivotal behavior at least 0.90 overall and at least 0.80 for every pivotal mechanism;
- invariance and contextual behavior 1.0;
- canonical queue-order exactness at least 0.95;
- executed/deferred exactness at least 0.95;
- no held-out renderer stratum below 0.85 decision accuracy.

Passing would support synthetic multi-event institutional reasoning under a held-out renderer. It would not authorize autonomous execution or establish real-institution validity.