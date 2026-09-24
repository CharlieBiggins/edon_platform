# EventNet Scaling Architecture

ACTIONNET-DATA-QUAL-004 adopts bounded architectural lessons from large agent-simulation systems without claiming billion-agent execution.

## Adopted now

### Deterministic event queue

All interactions become typed events with an explicit total order. This supports concurrency tests without allowing runtime scheduling accidents to decide institutional outcomes.

### Layered state

Authoritative external state is distinct from any future learned model's internal memory. A Cerebrum proposal may suggest an interpretation, but only the deterministic transition/evaluation path may produce a binding execution decision.

### Bounded operations

The current operation set covers authority, evidence, workflow, resources, routing, policy, conflict, request validity, and appeals. Unregistered operations fail closed.

### Safe aggregation

Only proven-commutative resource deltas may be compacted. Qualification compares compacted and sequential execution. No authority, policy, evidence, routing, conflict, or appeal event is aggregated.

### Multi-resolution metrics

Qualification preserves per-event receipts, per-trajectory certificates, counterfactual pair behavior, mechanism coverage, and aggregate outcome hashes.

## Deferred until measured

- learned routing among rules, small surrogates, Cerebrum, and larger models;
- compressed graph storage and vectorized execution;
- distributed event partitions;
- million- or billion-actor performance claims;
- hardware acceleration.

These require benchmarks showing that the deterministic CPU implementation fails a real latency, throughput, energy, or isolation requirement. Scale is not permitted to weaken semantic equivalence or the Kernel authority boundary.