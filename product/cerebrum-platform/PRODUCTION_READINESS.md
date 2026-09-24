# Production readiness

The Cerebrum Platform is not production authorized. The following gates remain
open.

## Architecture and contracts

- [x] Controlling successor vision frozen under `CEREBRUM-PLATFORM-VISION-002`.
- [x] Nine canonical specifications written or inherited.
- [x] Mature specification frozen with eleven canonical specifications.
- [x] Additive target JSON schemas written.
- [x] Vendor-neutral `CEREBRUM-PLATFORM-FOUNDATION-001` draft registered.
- [x] Replaceable `CEREBRUM-AWS-DEPLOYMENT-PROFILE-001` draft registered.
- [ ] All fourteen Platform Foundation freeze gates passed with evidence.
- [ ] AWS deployment profile qualified against its twelve profile gates.
- [ ] Schema fixtures, compatibility adapters, and migration tests completed.
- [ ] Public v1 API implemented and threat modeled.

## Platform services

- [ ] Control Plane implemented with tenant and compartment isolation.
- [ ] Institutional Control Graph implemented with replayable versions and
  service-owned lifecycle writes.
- [ ] Identity/capability, mandate, commitment, and reservation services implemented.
- [ ] Decision, execution, and compensation receipts implemented with signatures.
- [ ] Compensation Manager requires new Kernel authorization for recovery actions.
- [ ] Multidimensional state projection and conflict handling implemented.
- [ ] Kernel authorization separated from Execution Assurance.
- [ ] Credential Broker isolated from the Control Plane, Reasoning Runtime,
  Kernel, Execution Assurance identity, and connector credentials.
- [ ] External-system credentials bound to exact proposal, authorization,
  state, connector, resource, expiration, and idempotency identities.
- [ ] Native connectors, receipts, reconciliation, and compensation qualified.
- [ ] Outcomes return through validation, evidence admission, and versioned
  state projection rather than mutating state directly.
- [ ] Evaluation and Release Registry implemented with signatures.
- [ ] Deployment Controller, attestation, canaries, containment, and rollback implemented.
- [ ] Command Center and embedded decision cards implemented with accessible human recourse.
- [ ] Model and Solver Registry, enforceable routing policy, data grants,
  invocation receipts, budgets, and qualified fallbacks implemented.
- [ ] Mature ActionNet experience/learning contract enforced across custody,
  rights, review, training, evaluation, release, and deployment boundaries.

## Operational qualification

- [ ] First Qualified Operational Workflow selected and registered.
- [ ] Customer data rights, privacy, security, authority, and stop rules approved.
- [ ] Historical replay gates passed.
- [ ] Live read-only shadow gates passed.
- [ ] Assisted-operation gates passed before any consequential connector write.
- [ ] Independent security, resilience, and recovery assessments passed.
- [ ] Proposed SLOs replaced by measured, workload-specific targets and a dated
  infrastructure bill of materials.
- [ ] Production operating owner accepts the bounded capability envelope.

## Research boundary

- [ ] Matched ActionNet learning contribution reproduced as required for that claim.
- [ ] Independent transfer demonstrated as required for that claim.
- [ ] Governed closed-loop performance demonstrated as required for that claim.

Product implementation and scientific claims are tracked separately. Passing
one does not silently satisfy the other.