# Hierarchical institutional federation

EDON's federation reference implements the deployment principle:

> Think globally. Decide at the lowest authorized level. Optimize
> hierarchically. Execute locally. Learn through governed abstraction.

```text
Global scope
    -> domain scope
        -> regional scope
            -> facility scope
                -> edge scope
```

Each scope is tenant isolated, immutable, optionally bound to one local
institutional world, and assigned an authority domain and decision-latency
class. A child scope must be strictly below its parent. A tenant has one root.

## Governed projection

Local worlds do not send raw observations, payloads, people, packages, sensor
records, or memory entries upward. They emit a version-bound projection with:

- counts of goals, plans, agents, alerts, observations, and outcomes;
- aggregate resource capacity, allocation, availability, and utilization;
- source world version and state hash;
- `contains_raw_records=false` and `binding_authority=false`.

Parent scopes can aggregate child projections and publish a new aggregate to
their parent. Every level therefore reasons over the minimum registered state
rather than copying the entire institution into a model context.

## Cross-level routing

The deterministic router computes the least common ancestor of every affected
scope. A decision also moves upward when local impact, uncertainty, or required
authority exceeds its registered boundary. Escalations are append-only records
with acknowledgement and resolution events; they are not execution approvals.

## Optimization boundary

Cerebrum or an operator may formulate an objective, supplies, demands, lanes,
costs, and state hashes. An operations-research provider returns a candidate.
The adapter independently verifies known lanes, lane capacity, supply capacity,
demand limits, costs, and authority separation.

The included deterministic capacity allocator is a reproducible interface
fixture. It makes `optimality_claim=false`; production deployments should bind
reviewed specialist solvers behind the same validation and Kernel boundary.

## Current limitations

This is single-node SQLite federation. It does not implement network transport,
distributed consensus, replicated regional planes, enterprise identity,
source-grounded logistics models, production data residency, or learned
hierarchical planning. EDON-FED-001 is internal deterministic evidence only.