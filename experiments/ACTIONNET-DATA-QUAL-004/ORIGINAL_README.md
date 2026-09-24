# ACTIONNET-DATA-QUAL-004

Status: `READY_FOR_CEREBRUM_EVENTNET_DEVELOPMENT` after the frozen campaign is generated.

Frozen result identity: `ACTIONNET-DATA-QUAL-004-result-v1.0.0`.

This additive successor introduces a fresh, independent ActionNet implementation for deterministic multi-actor institutional event queues. It does not alter or replace `ACTIONNET-DATA-QUAL-003`, and it is not a reason to interrupt `CEREBRUM-DEV-002`.

The corpus models ordered and simultaneous events, authority revocation propagation, delayed evidence, approval withdrawal, resource contention, policy changes, cross-institution routing, jurisdiction changes, conflicts, malformed requests, priority races, evidence expiry, and unresolved appeals. Every queue is executed by two independent scheduler/transition/oracle paths. Safe aggregation is permitted only for proven-commutative resource deltas and is checked against unaggregated execution.

The frozen package contains:

- 5,040 training records;
- 420 repair-validation records;
- 600 canonical multi-actor trajectories;
- 300 registered counterfactual pairs;
- certificate, transition, queue-trace, and pair-contrast supervision;
- three training renderers and one lineage-isolated held-out renderer;
- 31 qualification controls, including byte-deterministic regeneration.

Run:

```bash
python run_campaign.py
python -m unittest discover -s tests -v
sha256sum -c results/checksums.sha256
```

This remains project-authored synthetic data. It is not source-grounded, human-domain-validated, independently replicated, public-confirmatory, or production-authoritative. The deterministic Kernel retains all binding authority.