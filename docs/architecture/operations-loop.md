# Governed institutional operations loop

The target platform places this bounded reference loop inside the Control
Plane. Its current authorization-reference behavior is not the final public
action lifecycle or Execution Assurance contract.

The internal operations reference connects EDON's persistent world and memory
stores to a deterministic coordination loop. Cerebrum or another planner may
propose goals, plans, assignments, or commands, but the proposal remains
non-binding until the institution-local authority layer supplies an
authorization reference and the expected world version still matches.

```text
typed observation
    -> governed episodic memory
    -> goal lifecycle
    -> validated acyclic plan
    -> deterministic readiness ordering
    -> capability and resource checks
    -> authorized assignment or atomic dispatch
    -> monitored outcome
    -> completion or corrective replan
    -> tenant-local, review-required ActionNet candidate
```

## Implemented internal capabilities

- typed ingestion for text, image, audio, video, sensor, telemetry, document,
  human-report, and system-event observations;
- dynamic goal states, priorities, deadlines, dependencies, owners, and parent
  goals;
- multi-step plans with dependency-cycle rejection, long time horizons,
  earliest starts, deadlines, expected outcomes, and additive revisions;
- human, software, service, and robot agent registrations with capabilities,
  concurrency limits, status, metadata, and relationship records;
- renewable and non-renewable resource pools with all-or-nothing capacity
  checks and atomic dispatch;
- deterministic, non-binding assignment recommendations across ready steps and
  available agents;
- outcome monitoring that distinguishes reported success from verified expected
  outcomes, releases resources, completes goals, or blocks them for replanning;
- deadline, unavailable-agent, resource-overallocation, and replan alerts;
- learning candidates derived from outcomes with
  `training_eligible=false` and `requires_authorized_review=true`.

Plan commands always carry `binding_authority=false`. A robot or external
service adapter may receive a command only after a separate production Kernel
validates the exact command, authority, policy, evidence, state version, and
execution token. This repository does not directly drive physical hardware.

## Transaction boundary

World changes are single-database event commits. Observation and outcome memory
use an idempotent two-store saga: the same identifiers can be retried after an
interrupted world/memory link. Production deployment requires a transactional
outbox or equivalent cross-service delivery guarantee.

## Remaining production work

The reference does not include camera/audio foundation models, enterprise
connectors, autonomous goal invention, a learned long-horizon planner,
production semantic retrieval, distributed consensus, cryptographic Kernel
token validation, online weight updates, or hardware-specific motor drivers.
Those components can connect through the implemented contracts without being
granted authority to bypass them.

Institutional memory supports context-only adaptation and is never implicitly
training eligible. Local ActionNet experience must pass a separate governed
promotion boundary before a de-identified abstraction may enter Global
ActionNet. No outcome or memory write directly changes C1 weights.