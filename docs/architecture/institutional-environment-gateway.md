# Institutional Environment Gateway

Status: `ARCHITECTURE_DEFINED_PARTIALLY_IMPLEMENTED_NOT_PRODUCTION_AUTHORIZED`

Under `CEREBRUM-PLATFORM-VISION-001`, this architecture is the partial
predecessor of the Observation and Connector Gateway. The target gateway keeps
the same evidence/authority separation while adding authorization-bound
Execution Assurance, connector reconciliation, outcome verification, and a
shared Event Envelope.

The Institutional Environment Gateway is the umbrella integration boundary
between EDON and the institution's complete action environment. The existing
Agent Gateway is one component of this boundary; the broader architecture also
covers enterprise systems and governed resources.

The design changes the unit of observation from “what an agent said” to “how
the institution changed.” The Cerebrum System projects the resulting evidence
into separated state views, and C1 may reason over those views; neither receives
authority to commit changes.

```text
Agents ──────┐
Systems ─────┼──> Institutional Environment Gateway ──> Observations
Resources ───┘                                             |
                                                            v
                                               Institutional World Model
                                                            |
                                                            v
                                                  Cerebrum System
                                             state + C1 proposals and plans
                                                            |
                                                            v
                                                Deterministic Kernel
                                              authorization and commit
                                                            |
                                                            v
                                      Transactional outbox + action adapter
                                                            |
                                                            v
                                               Institutional environment
                                                            |
                                                            v
                                         State changes and outcome receipts
                                                            |
                                                            v
                                      ActionNet governed experience candidate
                                                            |
                                                            `--> World Model
```

## Environment entity classes

The gateway uses three primary entity classes without treating them as
interchangeable:

| Class | Examples | State represented |
| --- | --- | --- |
| `AGENT` | people, software agents, robots, contractors | identity, role, capability, availability, assignment, reported action |
| `SYSTEM` | EHR, ERP, CRM, API, database, sensor, workflow engine | health, version, accessible operations, records, events, dependencies |
| `RESOURCE` | staff time, beds, money, inventory, vehicles, facilities, compute | quantity, capacity, location, reservation, eligibility, depletion, replenishment |

An adapter may expose more than one class, but every event identifies the
specific entity whose state is being described. An AI service, for example,
may be modeled as an agent when it proposes work, a system when it exposes an
API, and a resource when its compute quota is allocated. Those are separate
typed roles rather than one ambiguous object.

## Three data paths

### Observation path

External reports, telemetry, system events, capacity changes, and action
receipts enter as untrusted, non-authoritative environment events. Each event
records tenant, world, source, entity class, event time, observation time, the
time it became available to the controller, sensitivity, confidence,
provenance, and content hash. This supports prospective replay without giving a
controller information before it was actually available.

Because environment evidence may itself be compromised, a resilience-capable
deployment must support source diversity, conflict preservation, stale/replay
checks, provenance verification, confidence, and operation when one source or
adapter is unavailable. An apparently valid event is not automatically true.

### Authorized action path

C1 and external agents can submit only typed proposals. A binding command
must pass shadow supervision and deterministic policy checks, receive an
exact-request Kernel authorization, and enter the transactional outbox. A
target-specific action adapter may deliver only that authorized outbox record.
The general Agent Gateway envelope cannot carry a Kernel token or manufacture
authority.

### Experience path

EDON links the prior world state, available information, decision or proposal,
authorized action, observed state change, and verified outcome. This chain may
become an ActionNet experience candidate. Real operational records remain
source-bounded, review-required, overlap-unchecked, and training-ineligible
until the existing ActionNet custody and release gates approve them.

ActionNet therefore has three connected responsibilities:

1. it generates synthetic and counterfactual experience for bounded research;
2. it captures candidate experience derived from observed institutional change;
   and
3. it qualifies reviewed experience into content-bound training releases.

It is not merely a downstream log, and operational feedback never updates
model weights automatically.

## State-change semantics

The environment gateway reports evidence of change; it does not declare policy
or truth by itself. State reconciliation preserves distinctions among:

- reported versus independently verified outcomes;
- event occurrence time versus ingestion and controller-availability time;
- physical state versus normative permission;
- proposed, authorized, delivered, acknowledged, observed, and verified action
  states;
- quantities observed directly versus estimated or derived quantities.

Durable changes to EDON's institutional world still require version-bound world
events and deterministic commit. Conflicts between sources remain explicit for
review rather than being silently overwritten.

## Mapping to the current repository

| Capability | Current implementation |
| --- | --- |
| External agent protocol normalization | Agent Gateway protocol and custody core |
| Read-only healthcare ingress | Agent Gateway FHIR R4/SMART boundary |
| Persistent institutional state | Event-sourced world and snapshot stores |
| Agents, resources, plans, assignments, and outcomes | Operations layer |
| Exact-request authorization | Kernel token and commit boundary |
| Durable post-commit delivery record | Transactional outbox |
| Governed experience and training release | ActionNet Platform |

The general environment-event schema is defined at
`schemas/environment/event.schema.json`. It is a design contract and does not
mean that live adapters exist.

## Not implemented by this architecture record

- native ERP, CRM, EHR, database, sensor, finance, inventory, robotics, or
  facility adapters;
- a production asset/resource ontology or automatic entity resolution;
- authorized outbound delivery workers and target reconciliation;
- production identity, credential lifecycle, network security, rate limiting,
  high availability, or disaster recovery;
- verified causal attribution from an action to an institutional outcome;
- automatic promotion of operational events into ActionNet training data;
- real-institution closed-loop performance, safety, or transfer evidence.

The current Agent Gateway remains
`INTERNAL_PROTOCOL_CORE_NOT_PRODUCTION_AUTHORIZED`. The broader Institutional
Environment Gateway remains an architectural integration target.