# EDON Institutional Environment Gateway

Status: `ARCHITECTURE_DEFINED_PARTIALLY_IMPLEMENTED_NOT_PRODUCTION_AUTHORIZED`

This package is the current integration predecessor of the target Observation
and Connector Gateway in `product/cerebrum-platform/`. The target name does not
upgrade the implementation or connector qualification status.

The Institutional Environment Gateway is EDON's planned common boundary for
observing and acting upon an institution's complete action environment:

- agents, including people, software agents, and robots;
- systems, including EHR, ERP, CRM, APIs, databases, sensors, and workflow
  engines; and
- resources, including staff, facilities, money, inventory, vehicles, and
  compute.

Its purpose is to keep EDON's institutional world model synchronized with
time-gated evidence about real state changes while preserving the separation
between observation, reasoning, authorization, execution, and learning.

## Product decomposition

```text
Institutional Environment Gateway
├── Agent Gateway
├── System connectors
├── Resource-state adapters
├── Observation and telemetry intake
├── Kernel-authorized action adapters
├── Delivery and outcome reconciliation
└── ActionNet experience-candidate capture
```

Only the Agent Gateway protocol/custody core and the repository's internal
world, operations, Kernel, outbox, and ActionNet components currently exist.
The umbrella gateway does not yet provide production system or resource
connectors.

## Non-negotiable boundary

Inbound events are untrusted evidence. The Cerebrum System maintains separated
state views and C1 produces non-binding proposals. Only the deterministic
Kernel can authorize a binding state transition. An
outbound adapter may deliver a command only after it receives an exact-request,
version-bound authorized outbox record. Gateway connectors cannot mint,
reinterpret, or broaden that authorization.

See `docs/architecture/institutional-environment-gateway.md` for the canonical
architecture, `docs/architecture/institutional-resilience.md` for the bounded
adversarial-state and continuity direction, and `PRODUCTION_READINESS.md` for
the remaining work.