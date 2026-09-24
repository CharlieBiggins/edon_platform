# Institutional Environment Gateway production readiness

Current disposition:
`ARCHITECTURE_DEFINED_PARTIALLY_IMPLEMENTED_NOT_PRODUCTION_AUTHORIZED`.

## Present foundations

- typed agent/system/resource and environment-event contracts;
- Agent Gateway protocol normalization and immutable custody core;
- event-sourced institutional world state;
- typed agents, resources, plans, assignments, and outcomes;
- deterministic Kernel authorization and transactional outbox;
- ActionNet review, provenance, qualification, and training-release controls.

## Required before a live pilot

- identify one bounded institution, workflow, and accountable operational owner;
- inventory every source, target, agent, system, and resource in pilot scope;
- implement and test the required native read adapters in shadow mode;
- calibrate clocks, identifiers, units, availability rules, and reconciliation;
- establish production identity, secrets, consent, data rights, retention, and
  incident-response controls;
- create connector-specific conformance, replay, stale-state, outage, conflict,
  and adversarial tests;
- test state poisoning, compromised sources, cross-system cascades, authority
  confusion, resource exhaustion, and provenance loss under frozen timelines;
- document manual and deterministic degraded modes for gateway, model, source,
  and dependency failure;
- freeze the baseline, information-availability timeline, controller runtime,
  safety constraints, and scoring protocol;
- keep outbound delivery disabled until shadow results and independent safety
  review authorize a separately bounded action pilot.

## Required before binding operation

- independently reviewed Kernel policies and exact-request token lifecycle;
- target-specific delivery, acknowledgement, retry, dead-letter, and
  reconciliation semantics;
- version and state precondition checks immediately before every action;
- rollback or compensating-action procedures where physically possible;
- human escalation and emergency-stop procedures;
- least-privilege containment scopes, blast-radius limits, and independent
  rollback drills;
- external security, privacy, resilience, and domain-safety review;
- documented legal and organizational authorization from the institution.

No current repository result satisfies these production gates.