# Cerebrum Platform

Status: `MATURE_SPEC_001_FROZEN_FOUNDATION_001_DRAFT_NOT_PRODUCTION_AUTHORIZED`

This package is the unified target product boundary for Cerebrum. It does not
replace the existing component packages or claim that the complete platform has
been implemented. The controlling architecture is
`CEREBRUM-PLATFORM-VISION-002`.
The controlling product contract map is `CEREBRUM-MATURE-PLATFORM-SPEC-001`.
The vendor-neutral implementation draft is
`CEREBRUM-PLATFORM-FOUNDATION-001`. The first proposed cloud mapping is
`CEREBRUM-AWS-DEPLOYMENT-PROFILE-001`. Neither draft authorizes deployment,
regulated-data processing, customer commitments, or consequential writes.

Cerebrum is one horizontal institutional-intelligence platform with multiple
interfaces:

- **Control Plane:** Control Graph, authority/commitment services, reasoning,
  Kernel, execution/recovery, outcomes, audit, and release controls;
- **Intelligence API:** programmable institutional-task interface;
- **Command Center:** human supervision, approval, intervention, and audit;
- **embedded decision cards:** governed interaction inside existing systems.

## Authority doctrine

```text
Models propose.
Humans approve when required.
The Control Graph represents the institution.
Mandates define delegated authority.
Kernel authorizes.
Execution Assurance acts and verifies.
Receipts preserve proof.
Connectors interact.
Outcomes update the graph.
Reviewed evidence improves future releases.
The Deployment Controller governs installation.
```

## Platform composition

```text
Experience layer
  -> Control Plane
  -> Institutional Control Graph
  -> Model and Solver Registry / enforceable routing policy
  -> Reasoning Runtime
  -> Action Proposal
  -> Delegated Authority and Commitment Layer
  -> Independent Kernel
  -> Decision Receipt
  -> Execution Assurance and Recovery
  -> Execution Receipt
  -> Observation and Connector Gateway
  -> Operational systems
  -> Outcome and audit stream
  -> Reviewed ActionNet
  -> Evaluation and Release Registry
  -> Deployment Controller
  -> Reasoning Runtime
```

See `COMPONENTS.md` for current implementation mapping and
`PRODUCTION_READINESS.md` for the remaining work.

## Implementation foundation

The Foundation draft defines service and trust boundaries, a six-deployable
starting shape, PostgreSQL-first data custody, independent Kernel and deployment
control, proposal-bound credential isolation, authoritative receipts,
reliability controls, proposed pilot SLOs, and fourteen evidence-based freeze
gates.

The AWS profile maps those vendor-neutral requirements to managed AWS services.
It proposes ECS Fargate for CPU services, separately qualified GPU paths, RDS
PostgreSQL, S3/Object Lock receipt custody, EventBridge/SQS, Step Functions,
KMS/Secrets Manager, and independently governed release and deployment. It is
a replaceable profile rather than part of Cerebrum's frozen doctrine.

## Deployment rule

The horizontal core is combined with a versioned domain pack and a registered
First Qualified Operational Workflow. A domain pack does not grant permission
to act, and a successful workflow qualification does not authorize unrelated
workflows, sites, tenants, or operating modes.

## Control Plane services

The Control Graph represents identity, capability, mandates, commitments,
reservations, proposals, receipts, and outcomes. Dedicated services own each
lifecycle. Capability does not imply authority; a mandate does not replace a
Kernel decision; a reservation does not authorize consumption; and
compensation requires a new proposal and authorization.

Every model, solver, simulator, critic, perception service, and communication
component is separately registered, evaluated, deployed, permissioned,
budgeted, routed, and receipt bound. Provider-managed APIs use provider model,
API revision, deployment, and evaluation identities when inaccessible weights
cannot honestly be content hashed.

## Claim boundary

The package contains architecture, specifications, and schemas. Existing EDON
components provide partial internal reference foundations. No complete-platform
protected evaluation, qualified customer workflow, production deployment, or
binding-authority result exists.