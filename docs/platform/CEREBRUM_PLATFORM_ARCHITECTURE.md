---
document_id: CEREBRUM-PLATFORM-ARCHITECTURE-001
title: Cerebrum Platform Architecture
version: 0.2.0
status: CANONICAL_DRAFT
owner: EDON
last_updated: 2026-09-25
classification: INTERNAL
---

# Cerebrum Platform Architecture

## 1. Purpose

This is the canonical architecture specification for the EDON Cerebrum platform. It defines the platform doctrine, product surfaces, lifecycle layers, authority boundaries, security requirements, runtime profiles, current implementation status, production-readiness gates and canonical terminology.

This document must be read before changing platform architecture, lifecycle behavior, capability claims, security boundaries or terminology.

### 1.1 Source-of-truth rule

When documentation, UI fixtures and runtime behavior disagree:

1. Validated server behavior and canonical contracts take precedence.
2. The disagreement must be recorded as a defect.
3. UI and documentation must be corrected in the same change or a linked follow-up.
4. A simulated capability must never be represented as authoritative or production-ready.

### 1.2 Change-control rule

Any pull request that changes a platform layer, lifecycle, contract, capability status or authority boundary must update this document, applicable contracts, capability metadata, validation coverage and user-facing capability labels.

## 2. Platform mission

EDON builds institutional intelligence infrastructure. Cerebrum helps organizations understand institutional state, diagnose operational changes, coordinate across systems and locations, develop recovery plans, govern authority, verify outcomes and preserve defensible proof.

The research goal is to learn institutional reasoning once and transfer it to unseen organizations and domains without customer-specific model retraining. Customer institutions are represented through governed, versioned institutional context rather than by granting the learned model direct authority.

## 3. Governing doctrine

> C1 understands, diagnoses, plans, coordinates and proposes. The Kernel authorizes. Humans govern. Execution Assurance acts. Verified outcomes update the institution.

### 3.1 C1 may

- Interpret objectives, evidence, policies, commitments, resources and dependencies.
- Diagnose institutional changes and operational risk.
- Identify missing, conflicting or disputed evidence.
- Generate typed proposals and alternatives.
- Compare plans using cost, time, feasibility, risk and protected commitments.
- Reason counterfactually.
- Explain recommendations with evidence and context bindings.
- Monitor outcomes and propose revisions.

### 3.2 C1 may not

- Establish authoritative truth by itself.
- Grant authority or modify mandates.
- Approve its own proposal or override the Kernel.
- Hold customer write credentials or dispatch production commands directly.
- Modify production policy.
- Sign authoritative receipts.
- Activate an Institution Pack or model release.
- Learn directly from production outside the governed release process.

### 3.3 Authority separation

| Responsibility | Authoritative component |
| --- | --- |
| Customer identity and membership | Identity and Access Layer |
| Canonical institutional state | Control Plane and State Projector |
| Institutional relationships | Institutional Control Graph |
| Learned reasoning | Cerebrum C1 |
| Policy and authority evaluation | Independent Kernel |
| Human authorization | Command Center Human Review |
| External action | Execution Assurance |
| Outcome verification | Outcome and Reconciliation Services |
| Durable proof | Receipts and Forensic Reconstruction |
| Model deployment | Model Release Registry and Deployment Controller |
| Institution Pack deployment | Institution Release Registry and Deployment Controller |

## 4. Product surfaces

### 4.1 Cerebrum Command Center

The customer-facing operational and governance experience includes Operations Overview, Work Queue, Cerebrum Workspace, Ask Cerebrum, Human Reviews, Shadow and Outcomes, Reconstructions, Receipts, Execution Exceptions, Integrity, Legal Holds, Audit Exports, Verified Value, Institution Builder, Intelligence Runtime, Institutional State, Integrations and Settings.

### 4.2 Cerebrum Control Plane

The authoritative backend is responsible for tenant-scoped persistence, source and evidence custody, event admission, state projection, Control Graph state, proposal binding, Kernel decisions, human reviews, execution commands, outcomes, receipts, reconstruction, and institution/model release registries.

### 4.3 Cerebrum Intelligence API

The governed interface to qualified intelligence runtimes provides context assembly, C1 invocation, structured proposals, explanations, solver invocation, capability checks and invocation metadata. It is not an authorization system and cannot execute customer actions.

## 5. Complete lifecycle

```text
Customer onboarding
→ tenant and identity configuration
→ institution compilation
→ validation and qualification
→ signed Institution Pack
→ shadow deployment
→ observation and evidence admission
→ state projection
→ C1 reasoning
→ proposal
→ Kernel decision
→ human review when required
→ governed execution
→ outcome verification and reconciliation
→ signed receipts and reconstruction
→ verified value
→ governed learning and release
```

The architecture is divided into:

1. Customer onboarding and tenant setup.
2. Institution onboarding and compilation.
3. Qualification and shadow deployment.
4. Production observation and institutional state.
5. Intelligence and reasoning.
6. Decision governance.
7. Production execution.
8. Outcomes, recovery and reconciliation.
9. Auditability, assurance and forensic proof.
10. Learning and model release.
11. User experience surfaces.
12. External product interfaces.
13. Security and production foundation.
14. Platform operations and customer governance.

## 6. Customer onboarding and tenant setup

| Layer | Responsibility | Type |
| --- | --- | --- |
| Tenant Provisioning | Create tenant, regions, facilities and environments | Backend |
| Identity Integration | Connect OIDC, SSO and directory services | Backend |
| Membership Service | Bind actors to tenants, roles and facilities | Backend |
| Capability Authorization | Enforce action-specific permissions | Backend |
| Tenant Isolation | Enforce boundaries in APIs, transactions and PostgreSQL RLS | Backend |
| Data Classification | Define sensitivity and handling requirements | Shared |
| Support Access Governance | Control temporary EDON access | Backend |
| Environment Configuration | Separate local, staging, shadow and production | Infrastructure |

Required outputs:

```text
Tenant identifier
Organization profile
Facility and regional scope
OIDC issuer and membership bindings
Roles and capabilities
Data-classification and retention policy
Support-access policy
Approved runtime profile
```

Invariants:

- Tenant and actor identity derive from a verified principal, not request-body claims.
- Every authoritative record is tenant-bound.
- Facility scope is enforced when resources or mandates are facility-limited.
- Employment title or founder status does not grant customer-content access.
- Customer support access is purpose-bound, time-limited and audited.

## 7. Institution onboarding and compilation

The Institution Builder is the governed administrative UI for candidate institutional representations. The Institution Compiler is the server-only backend that deterministically produces versioned Institutional IR and release artifacts. The Builder does not activate policy, grant authority, enable connectors or permit production execution by itself.

### 7.1 Exact ten-stage vocabulary

The UI, contracts, compiler, audit events and documentation must use:

1. `SOURCES`
2. `CLASSIFICATION`
3. `EXTRACTION`
4. `IR_MAPPING`
5. `VALIDATION`
6. `AUTHORITY_POLICY`
7. `CONTROL_GRAPH`
8. `SIMULATION`
9. `REVIEW_SIGN`
10. `DEPLOYMENT`

The UI may visually group stages but must not rename, merge or skip them.

```text
SETUP
01 Sources
02 Classification

INSTITUTIONAL MODEL
03 Extraction
04 IR Mapping
05 Validation

GOVERNANCE
06 Authority & Policy
07 Control Graph

QUALIFICATION
08 Simulation
09 Review & Sign
10 Deployment
```

### 7.2 Stage 1: Sources

Collect policies, SOPs, organization charts, contracts, schemas, workflows, approval matrices, historical cases, resources and connector definitions.

Every source record requires:

```text
tenant_id
institution_id
source_id
source_version
source_type
owner_id
provenance
sensitivity
effective_from
effective_to
content_hash
ingested_at
classification_status
```

### 7.3 Stage 2: Classification

Classify owner, provenance, sensitivity, effective dates, retention, allowed uses, facility/region scope and whether information is observed, reported, inferred, authorized or committed.

### 7.4 Stage 3: Extraction

Models may propose typed candidate facilities, people, systems, agents, resources, commitments, policies, mandates and workflows. Model-produced objects remain candidates until validated and approved.

### 7.5 Stage 4: IR Mapping

Map customer terminology and source fields into canonical Institutional IR while preserving customer terminology as aliases.

| Customer term | Canonical concept |
| --- | --- |
| Shipment order | Commitment |
| Dock door | Resource |
| Operations manager | Actor |
| Service-level agreement | Constraint |
| Inventory shortage | Evidence |
| Carrier acceptance | Acknowledgement |
| Recovery plan | Proposal |

### 7.6 Stage 5: Validation

Deterministic validators detect invalid schemas, missing identifiers, broken references, conflicting policies, missing ownership, ambiguous authority, expired limits, unsupported transitions, unresolved connectors and incompatible model/domain-pack requirements.

Compilation fails closed when authority, policy, evidence or state ambiguity can affect a decision.

### 7.7 Stage 6: Authority & Policy

Represent request, control and approval rights; financial and capacity limits; facility boundaries; mandate activation and expiry; separation of duties; evidence requirements; prohibited actions; escalation paths; and break-glass rules. The compiler represents authority but does not grant it.

### 7.8 Stage 7: Control Graph

Generate and preview entities, typed relationships, dependencies, resource ownership, commitments, restrictions, evidence relationships and connector mappings. The UI shows a structured diff between active and candidate graphs.

### 7.9 Stage 8: Simulation

Run historical replay, boundary, failure, revoked-authority, missing-evidence, stale-state, adversarial, counterfactual and in-scope cross-facility cases. Simulation cannot activate a candidate.

### 7.10 Stage 9: Review & Sign

Authorized reviewers inspect source manifest, IR, graph diff, policy/authority mappings, validation findings, simulation results, compatibility and release metadata. Approval and signing are separate from authoring. KMS signs the exact approved manifest.

### 7.11 Stage 10: Deployment

```text
SIGNED
→ SHADOW
→ monitored qualification
→ limited production when authorized
→ broader production promotion
```

Rollback remains available to authorized actors.

### 7.12 Compiler artifacts

```text
Source Manifest
Institutional IR
Control Graph
State Model
Evidence Rules
Policy Pack
Authority Graph
Commitment Definitions
Workflow and Action Schemas
Connector Mappings
Simulation Report
Qualification Report
Release Manifest
KMS Signature
```

### 7.13 Institution release lifecycle

```text
DRAFT → EXTRACTED → MAPPED → VALIDATED → QUALIFIED
→ APPROVED → SIGNED → SHADOW → ACTIVE
```

Terminal or replacement states: `REJECTED`, `SUPERSEDED`, `ROLLED_BACK`.

### 7.14 Compiler invariants

- `Compile candidate` and `Activate release` are separate operations.
- Identical canonical sources, compiler version and configuration produce an identical IR hash.
- Compilation runs server-side, not in the browser.
- Inputs and outputs are versioned and immutable after approval.
- The compiler cannot grant authority, change production policy or enable execution.
- Every stage transition is authorized, tenant-scoped and journaled.
- Illegal stage skips are rejected unless represented as an authorized rollback or new version.
- Human approval binds to exact source, IR, policy, graph, compiler and validation hashes.

## 8. Qualification and shadow deployment

| Gate | Required proof |
| --- | --- |
| Structural | Schemas, identifiers, references and transitions pass |
| Governance | Ownership, policy, mandates and authority are unambiguous |
| Behavioral | Historical, failure and adversarial simulations pass |
| Release | Authorized reviewers approve and KMS signs the exact artifact |

In shadow mode:

- C1 has no production connector credentials.
- The evaluator has no dispatch path.
- Recommendations may be compared with actual outcomes.
- Operators may review without enabling execution.
- Every claim remains labeled simulated, inferred, observed, reported or verified.

Promotion requires a qualified Institution Pack, qualified C1 release, Kernel validation, customer approver, scoped credentials, Execution Assurance, reconciliation plan, monitoring, rollback and successful managed-staging qualification.

## 9. Production observation and institutional state

### 9.1 Observation and Connector Gateway

The gateway receives customer information and creates canonical event envelopes. Connectors may include ERP, WMS, TMS, MES, EHR, CRM, maintenance, financial, telemetry and human-report sources. Credentials remain inside the connector boundary and are never exposed to C1.

### 9.2 Canonical timestamps

Evidence distinguishes occurrence time, observation time, controller-availability time and recording time.

### 9.3 Evidence states

```text
OBSERVED
REPORTED
INFERRED
VERIFIED
DISPUTED
RESTRICTED
REJECTED
MISSING
```

Corrections create new records and relationships rather than rewriting history.

### 9.4 Append-only journal

Canonical events include:

```text
OBSERVATION_RECEIVED
EVIDENCE_ADMITTED
STATE_PROJECTED
MODEL_INVOKED
PROPOSAL_CREATED
KERNEL_DECIDED
HUMAN_REVIEWED
COMMAND_CREATED
COMMAND_DISPATCHED
ACKNOWLEDGEMENT_RECEIVED
OUTCOME_OBSERVED
OUTCOME_VERIFIED
RECONCILIATION_REQUIRED
RECEIPT_SIGNED
INSTITUTION_RELEASED
MODEL_RELEASED
```

### 9.5 State Projector

Every transition contains tenant/scope, previous and next version, canonical hash, state diff, contributing events, correlation/trace identifiers, timestamp and projector version. Optimistic concurrency prevents conflicting updates from advancing the same state.

Institutional state categories are observed, reported, inferred, authorized, committed and verified outcome. UI and API must not present inferred or reported information as verified truth.

### 9.6 Institutional Control Graph

The versioned graph represents facilities, people, teams, agents, robots, systems, resources, budgets, equipment, policies, constraints, objectives, commitments, ownership, authority, evidence relationships and dependencies. It is reconstructed from authoritative records, not visualization fixtures.

## 10. Intelligence and reasoning

### 10.1 Intelligence API

The API accepts typed context, verifies qualified releases, records model/adapter/ActionNet/domain-pack versions, binds context and evidence hashes, enforces timeouts/output schemas, returns typed outputs and fails closed through `ABSTAIN` for malformed, timed-out or unsupported output.

### 10.2 C1 Core Reasoning

C1 reasons across facilities, teams, agents, robots, operational systems, budgets, inventory, equipment, policies and commitments. Its differentiation is cross-boundary institutional reasoning rather than isolated task optimization.

### 10.3 Typed proposals

```json
{
  "disposition": "APPROVAL_REQUIRED",
  "objective": "Protect four delivery commitments",
  "actions": [],
  "required_resources": [],
  "expected_cost": 24600,
  "expected_recovery_hours": 6.5,
  "evidence_references": [],
  "assumptions": [],
  "authority_required": [],
  "state_version": 142
}
```

Each proposal binds to tenant/scope, incident, state version, relevant-state hash, evidence, policy, authority, mandates, commitments, model, adapter, ActionNet, domain pack, compiler and Institution Pack versions.

## 11. Decision governance

The independent deterministic Kernel evaluates state freshness, proposal integrity, evidence, policy, mandates, limits, facility scope, separation of duties, approval requirements and release qualification.

Canonical dispositions:

```text
ALLOW
DENY
ABSTAIN
ESCALATE
REVISE
REASSIGN
APPROVAL_REQUIRED
```

Human review requires an authenticated authorized reviewer, exact proposal/context hashes, mandate enforcement, duplicate protection, Kernel reevaluation and an immutable event.

Separation of duties:

- C1 cannot authorize its proposal.
- A compiler author should not approve the same release.
- EDON deployment personnel cannot grant customer authority.
- Production promotion requires a different permission from shadow deployment.
- Break-glass access cannot bypass receipt, identity, audit or policy controls.

## 12. Production execution

Execution Assurance is the only layer permitted to dispatch authorized external action. It binds commands to decisions and state, obtains scoped credentials, applies idempotency, dispatches through approved adapters, records acknowledgements and manages cancellation, compensation and takeover.

Execution modes:

```text
DISABLED
SHADOW_ONLY
APPROVAL_REQUIRED
LIMITED_EXECUTION
PRODUCTION_EXECUTION
```

Shadow must be physically incapable of dispatch: no production credentials, adapter binding, hidden route or implicit production fallback.

```text
COMMAND_CREATED
→ AUTHORIZATION_BOUND
→ DISPATCH_PENDING
→ DISPATCHED
→ ACKNOWLEDGED
→ IN_PROGRESS
→ COMPLETED | PARTIAL | FAILED | UNKNOWN
→ RECONCILED | COMPENSATED | HUMAN_TAKEOVER
```

Every transition is immutable, tenant-scoped and idempotent.

## 13. Outcomes, recovery and reconciliation

Outcome states:

```text
OBSERVED
VERIFIED
PARTIAL
DISPUTED
UNKNOWN
RECONCILIATION_REQUIRED
COMPENSATED
```

Verification records outcome source/evidence, independence, execution/proposal/decision bindings, timestamps, verification status and remaining disputes.

Reconciliation handles missing acknowledgements, partial completion, conflicting sources, duplicates, unknown external state, compensation and takeover. Unknown outcomes are never silently classified as successful.

Value reporting separates modeled, observed, verified, attributed and disputed value. It may evaluate commitments protected, downtime avoided, capacity gained, delay reduced, recovery time, cost avoided, incremental revenue and intervention burden.

## 14. Auditability, assurance and forensic proof

### 14.1 Decision receipts

Receipts bind tenant, actor, state, evidence, proposal, Kernel disposition, review, commands, outcomes, policy, authority, Institution Pack, model versions, correlation/trace identifiers, canonical hash and KMS metadata.

Unsigned authoritative receipts remain `SIGNATURE_PENDING`.

### 14.2 Receipt custody

- Production and staging use asymmetric KMS custody.
- Local deterministic signing is limited to local or explicit staging-test profiles.
- KMS outage fails closed.
- Duplicate signing is rejected.
- Rotation is governed and alias-based; historical keys remain for verification.
- Rotation creates `KMS_KEY_ROTATED`.

### 14.3 Forensic reconstruction

Reconstruction supports cutoff timestamp or journal offset, deterministic ordering, state replay/diffs, evidence availability, actors/authority, model invocations, proposals, decisions, reviews, commands, outcomes, restricted omissions and carefully typed causal relationships.

Causal status:

```text
CORRELATED
DEPENDED_ON
INFLUENCED
PRECEDED
CLAIMED_CAUSE
ADJUDICATED_CAUSE
```

Temporal sequence alone does not establish causation.

### 14.4 Signed evidence export

```text
manifest.json
timeline.jsonl
state-snapshots.jsonl
state-diffs.jsonl
evidence-index.json
actors.json
authority.json
model-invocations.jsonl
proposals.jsonl
kernel-decisions.jsonl
human-reviews.jsonl
commands.jsonl
outcomes.jsonl
integrity-report.json
human-readable-report.pdf
signatures/manifest.signature.json
```

Exports require tenant-scoped authorization and obey legal holds and restricted-evidence rules.

## 15. Learning and model release

ActionNet contains institutional situations, policies, counterfactuals, multi-agent coordination, failures, red-team cases, verified outcomes and abstention/escalation examples.

Production does not modify the deployed model directly:

```text
Verified outcome
→ de-identification and rights check
→ candidate learning record
→ dataset review
→ ActionNet release
→ training
→ evaluation
→ qualification
→ signed model release
→ shadow deployment
→ governed promotion
```

Each C1 capability manifest declares release status, model/adapter hashes, ActionNet, qualified workflows/domains, evaluations, safety constraints, unsupported conditions, latency/cost limits, fallback, authority and qualification/expiry timestamps.

Model release states:

```text
DRAFT
EVALUATING
QUALIFIED_SHADOW
QUALIFIED_LIMITED
QUALIFIED_PRODUCTION
SUSPENDED
SUPERSEDED
REVOKED
```

## 16. User experience and access

| Surface | Primary users |
| --- | --- |
| Operations Overview | Executives and operators |
| Work Queue | Operational teams |
| Cerebrum Workspace / Ask Cerebrum | Operators, analysts and reviewers |
| Human Reviews | Authorized decision reviewers |
| Shadow and Outcomes | Operational leaders and evaluators |
| Reconstructions / Receipts | Investigators and auditors |
| Integrity / Legal Holds / Audit Exports | Security, legal and compliance |
| Verified Value | Executives, finance and customer success |
| Institution Builder | Institution architects and administrators |
| Intelligence Runtime | Model and platform administrators |
| Institutional State / Integrations / Settings | Authorized administrators |

### 16.1 Institution Builder roles

| Role | Access |
| --- | --- |
| Operator | None |
| Human reviewer | Proposal review only |
| Source owner | View and confirm assigned sources |
| Policy owner | Review policy and authority mappings |
| Institution architect | Build and edit candidates |
| Security/data administrator | Review sensitivity, retention and connectors |
| Release approver | Approve or reject qualified releases |
| Auditor/investigator | Read-only history and signatures |
| EDON deployment engineer | Tenant-scoped access with customer authorization |

An Operator persona must not see an enabled Institution Builder entry.

## 17. EDON access to customer networks

Without a customer data grant, EDON personnel may see only service health, versions, connector status, counts, latency/errors, queue health, model usage, signing health, security alerts and sanitized logs.

Explicit purpose-bound grants may expose schemas, mappings, graph structure, supplied policies, authority definitions, workflows, validation failures, replay results, masked samples and candidate packs.

Raw operational records, PII/PHI, employee/financial data, restricted evidence, legal-hold material, full exports, production commands, credentials, secrets and key material are never broadly available by default.

```text
Customer opens case
→ grants scope
→ named EDON engineer
→ MFA and just-in-time access
→ tenant/facility/data/time limits
→ every view/export journaled
→ customer notified
→ automatic expiry
→ signed access receipt
```

## 18. External interfaces

| Interface | Purpose |
| --- | --- |
| Control Plane API | Authoritative lifecycle operations |
| Intelligence API | C1 reasoning and typed proposals |
| Event Ingestion API | Customer observations and events |
| Decision Card | Embed recommendations in customer applications |
| Receipt API | Retrieve verifiable receipts |
| Reconstruction API | Investigation, replay and exports |
| SDKs | Customer application integration |
| Webhooks and Outbox Delivery | Governed notifications |
| Connector Framework | Customer system integration |

Customers may retain their existing operational screens and use Cerebrum through APIs, embedded decision cards and audit integrations.

## 19. Security and production foundation

### 19.1 Persistence and transactions

- PostgreSQL is the authoritative persistent store.
- Mutating command stages use real `BEGIN`, `COMMIT` and `ROLLBACK`.
- One database client is used from transaction start to finish.
- Tenant context is transaction-local.
- API success is emitted only after commit.
- Optimistic state updates prevent stale writes.
- Idempotency is scoped by tenant and operation.

### 19.2 Row-level security

- Tenant-scoped tables use PostgreSQL RLS.
- Application roles cannot bypass RLS.
- Journal events and receipts are append-only.
- Mutation privileges are minimized by service identity.
- Tenant-isolation attack tests run in staging validation.

### 19.3 Transactional outbox

The outbox provides restart-safe, at-least-once processing with atomic enqueue, tenant/operation dedupe keys, `PENDING`, `PROCESSING`, `COMPLETED` and `DEAD_LETTER` states, expiring leases, `FOR UPDATE SKIP LOCKED`, bounded retry, error metadata, idempotent handlers and governed requeue events.

### 19.4 Authentication

OIDC verifies allowed algorithm, signature, issuer, audience, expiration, not-before time, key identifier, tenant membership, actor status, role and capabilities. Unknown signing keys trigger bounded JWKS refresh; verification fails closed.

### 19.5 Secrets and cryptography

- Secrets are stored in a managed secret service.
- Receipt and release signing use asymmetric KMS keys.
- Storage encryption uses a separate key.
- Services never receive raw KMS private key material.
- Production profiles reject local custody.

### 19.6 Evidence storage

Evidence object storage is encrypted and versioned, uses Object Lock and lifecycle retention where required, blocks public access and enforces tenant/role/purpose scope.

## 20. Runtime profiles

### 20.1 `LOCAL`

Permitted: memory repositories, simulated identity, deterministic custody and fixtures. Production dispatch is unavailable. Required labels: `LOCAL`, `SIMULATED`, `NOT AUTHORITATIVE`.

### 20.2 `STAGING_TEST`

Permitted: ephemeral PostgreSQL, temporary OIDC issuer, deterministic test KMS provider and service-container validation. Production dispatch is unavailable.

### 20.3 `STAGING`

Requires managed PostgreSQL, real OIDC/JWKS, KMS custody, tenant isolation, audit logging, secrets, observability, backup/restore, migration gates and no local fallback.

### 20.4 `PRODUCTION`

Requires all staging controls plus an approved Institution Pack, qualified production C1 release, customer-approved execution mode, scoped credentials, incident response, disaster recovery, retention/residency controls and continuous access review.

Staging and production runtimes fail startup when an authoritative dependency is unsafe or missing.

## 21. Managed infrastructure topology

The intended managed deployment includes:

- Private VPC networking.
- TLS load balancer and WAF ingress.
- Private container service runtime.
- Separate API, worker and migrator IAM identities.
- Managed encrypted PostgreSQL with backups and deletion protection.
- Encrypted evidence storage.
- Separate KMS keys for signing and storage encryption.
- Managed secrets.
- Private endpoints for required cloud services.
- Central logs, metrics, traces and alarms.
- Autoscaling boundaries.
- Remote Terraform state and locking.
- GitHub OIDC deployment without permanent cloud credentials.
- Migration-gated deployment.

Deployment sequence:

```text
Validate infrastructure code
→ review Terraform plan
→ provision infrastructure
→ run migrator
→ verify migration success
→ start API and worker
→ verify health/readiness
→ run qualification
→ enable staging traffic
```

API and worker desired count remains zero until the migrator succeeds on an initial gated deployment.

## 22. Observability and reliability

Required signals include API availability/latency/errors, database health, outbox states and oldest age, lease recovery, OIDC/authorization failures, signing failures, connector availability, model timeout/schema failure/abstention, projection freshness/conflicts, reconciliation backlog, and cost anomalies.

`/healthz` indicates process liveness. `/readyz` indicates dependency readiness and fails when required authoritative dependencies are unavailable.

Durability validation compares tenant-scoped canonical counts and hashes after initial lifecycle execution, API/worker restart, and database backup/restore. Mutating security tests must not contaminate the operational durability scope.

## 23. Capability status vocabulary

| Status | Meaning |
| --- | --- |
| `DESIGNED` | Architecture or contracts defined; no executable implementation |
| `UI_SIMULATED` | Experience exists with fixtures or simulated behavior |
| `REFERENCE_IMPLEMENTED` | Executable local or test implementation exists |
| `STAGING_VALIDATED` | Behavior passed staging-equivalent validation |
| `QUALIFIED_SHADOW` | Qualified for a specific shadow workflow and boundary |
| `PRODUCTION_READY` | Deployed and proven against production requirements |

Rules:

- `UI_SIMULATED` does not imply backend implementation.
- `REFERENCE_IMPLEMENTED` does not imply persistent secure production operation.
- `STAGING_VALIDATED` does not imply managed staging is deployed.
- `QUALIFIED_SHADOW` does not imply production execution authority.
- `PRODUCTION_READY` requires deployed infrastructure, real identity, KMS, monitoring, recovery and customer-specific qualification.
- Status is scoped; one workflow may be qualified while another remains designed.

## 24. Current implementation snapshot

This snapshot is dated **2026-09-25**. Code and CI remain authoritative.

| Capability | Status | Notes |
| --- | --- | --- |
| Command Center shell/navigation | `STAGING_VALIDATED` | Critical UI flows validated |
| Operations Overview / Work Queue | `UI_SIMULATED` | Operational data remains fixture-heavy |
| Cerebrum Workspace / Chat Focus | `STAGING_VALIDATED` | UI behavior validated; answers remain simulated unless API-backed |
| Ask Cerebrum citations/context | `UI_SIMULATED` | Live intelligence integration incomplete |
| Browser-safe contracts | `STAGING_VALIDATED` | Shared package boundary established |
| Control Plane HTTP API | `STAGING_VALIDATED` | Lifecycle routes validated through HTTP |
| PostgreSQL transactions | `STAGING_VALIDATED` | Real transaction and tenant context implemented |
| OIDC/JWKS verification | `STAGING_VALIDATED` | Strict validation in staging-equivalent tests |
| Capability authorization | `STAGING_VALIDATED` | Continue resource-coverage expansion |
| PostgreSQL RLS | `STAGING_VALIDATED` | Isolation attack tests implemented |
| Transactional outbox/worker | `STAGING_VALIDATED` | Leases, retries, dead letter and crash recovery |
| Observation/evidence lifecycle | `STAGING_VALIDATED` | Deterministic admission and immutable events |
| State projection | `STAGING_VALIDATED` | Snapshots, diffs, hashes and concurrency |
| Proposal/Kernel lifecycle | `STAGING_VALIDATED` | Context binding and decisions |
| Human review reevaluation | `STAGING_VALIDATED` | Exact bindings and mandate enforcement |
| Execution Assurance foundation | `REFERENCE_IMPLEMENTED` | Production connector dispatch disabled |
| Outcome reconciliation | `REFERENCE_IMPLEMENTED` | Production verification incomplete |
| KMS Receipt Custody | `STAGING_VALIDATED` | Managed KMS deployment pending |
| Break-glass governance | `STAGING_VALIDATED` | Tenant-scoped validation implemented |
| Forensic reconstruction/export | `REFERENCE_IMPLEMENTED` | Deterministic package validation exists |
| C1 capability registry | `REFERENCE_IMPLEMENTED` | Versioned manifests and API/UI surfaces |
| C1 logistics research release | `QUALIFIED_SHADOW` | Bounded synthetic/reference workflow only |
| Institution Builder UI | `UI_SIMULATED` | Must show simulated/candidate-not-active labels |
| Institution Compiler module | `REFERENCE_IMPLEMENTED` | Server-only foundation; authoritative release path incomplete |
| Persistent source registry | `DESIGNED` | Full persistence path incomplete |
| Institution release registry | `DESIGNED` | Review/sign/deploy/rollback incomplete |
| Real customer connectors | `DESIGNED` | Credentials and dispatch intentionally unavailable |
| Managed AWS staging | `DESIGNED` | Terraform audited; apply blocked pending configuration and plan review |
| Managed staging qualification | `DESIGNED` | Environment not provisioned |
| Real-institution shadow pilot | `DESIGNED` | Not completed |
| Production execution | `DESIGNED` | Intentionally disabled |
| ActionNet production learning | `DESIGNED` | Governed feedback pipeline incomplete |

## 25. Repository boundaries

```text
packages/contracts/          browser-safe and shared contracts
packages/platform-core/      server-only authoritative lifecycle
packages/platform-testkit/   scenarios and validation harnesses
apps/control-plane-api/      authenticated API and runtime profiles
apps/command-center/         declared frontend boundary
command-center/              existing Vite prototype during migration
infra/aws/staging/           managed staging infrastructure
scripts/                     validation and lifecycle scripts
docs/platform/               canonical architecture documentation
```

Browser code must not import Kernel, journal, receipt signing, repositories, KMS providers, server mandates or test fixtures as authoritative runtime behavior. The frontend uses browser-safe contracts and authenticated APIs.

## 26. Production-readiness gates

### 26.1 Functional

- Canonical lifecycle passes through HTTP.
- Negative paths are tested.
- Stale state fails closed.
- Duplicate commands are idempotent.
- Unknown outcomes require reconciliation.
- Rollback or compensation exists where required.

### 26.2 Security

- Real OIDC/JWKS.
- Tenant/facility isolation.
- Resource-level authorization.
- Secrets excluded from browser/model context.
- KMS custody and verification.
- Append-only authoritative records.
- Break-glass lifecycle and access review.

### 26.3 Durability

- Real transactions.
- Restart recovery.
- Backup/restore equality.
- Outbox crash recovery.
- Idempotent external delivery.
- Migration recovery plan.

### 26.4 Operations

- Managed staging deployment.
- Health/readiness.
- Logs, metrics, traces and alarms.
- Incident runbooks.
- Cost budgets.
- Load and connection-loss tests.
- Disaster-recovery test.

### 26.5 Customer

- Data/security agreements.
- Approved Institution Pack.
- Qualified C1 release.
- Authorized reviewers.
- Approved connector scope.
- Historical replay and shadow evaluation.
- Verified-value method.
- Customer-approved production promotion.

## 27. Institution Compiler acceptance test

The Builder may move from `UI_SIMULATED` toward `QUALIFIED_SHADOW` only when managed staging proves:

1. Authorized tenant-scoped source ingestion.
2. Persistent owner, provenance, sensitivity, dates and content hash.
3. Deterministic versioned Institutional IR.
4. Identical input/version/configuration produces the same IR hash.
5. Invalid mappings and ambiguous authority fail closed.
6. Persistent Control Graph diff.
7. Persistent historical/adversarial qualification results.
8. A distinct authorized reviewer approves exact hashes.
9. KMS signs the approved release.
10. Only shadow deployment is permitted within scope.
11. Transitions survive API, worker and database restart.
12. Backup/restore reproduces canonical hashes.
13. Cross-tenant access and mutation fail.
14. Command Center reads institutional state through authenticated APIs.
15. Rollback restores the previous qualified release without deleting history.

Until then, display:

```text
SIMULATED
CANDIDATE IR · NOT ACTIVE
```

## 28. Non-functional requirements

### 28.1 Determinism

Canonical serialization, hashes, replay order, compiler/projector versions and explicit reference time are required.

### 28.2 Explainability

Recommendations identify evidence, assumptions, alternatives, expected impact, uncertainty, missing information, required authority and reasons for escalation or abstention.

### 28.3 Availability and recovery

Before production define availability target, recovery time objective, recovery point objective, backup frequency, restore-test frequency and maximum reconciliation backlog.

### 28.4 Accessibility

UI maintains keyboard operation, focus visibility, contrast, screen-reader labels, non-color indicators, responsive layouts without clipping and automated accessibility validation.

### 28.5 Capability honesty

Never imply simulated data is live, modeled exposure is verified loss, a recommendation is authorized, shadow performed execution, a reported outcome is verified, a local signature is production KMS custody, or staging-equivalent tests prove managed production readiness.

## 29. Architectural invariants

1. C1 never grants authority.
2. The Kernel remains independent and deterministic.
3. Humans govern bounded approvals.
4. Execution credentials are unavailable to C1.
5. Shadow has no production dispatch path.
6. Authoritative records are tenant-scoped.
7. Tenant identity derives from verified authentication.
8. Journal and receipt records are append-only.
9. Success is returned only after commit.
10. External work occurs outside transactions through durable messages.
11. Repeated delivery is safe through idempotency.
12. Unknown outcomes remain unknown until reconciled.
13. Reported, inferred and verified state remain distinct.
14. Model failure produces abstention, never implicit authorization.
15. Compilation and activation are separate.
16. Model qualification and deployment are separate.
17. Decisions bind to exact context and versions.
18. Authoritative releases are signed and reconstructable.
19. Customer and EDON support access are explicit and auditable.
20. Capability labels never exceed validated status.

## 30. Highest-priority roadmap

### 30.1 Institution release transition boundary

`INSTITUTION_RELEASE_TRANSITION_V1` is **STAGING_QUALIFIED** as of merge commit
`4728bcce2d492563598f6b6722125f556938cfa3`. The staging-equivalent workflow
passed PostgreSQL rollback injection at `AFTER_CAS`, `AFTER_JOURNAL_APPEND` and
`AFTER_OUTBOX_ENQUEUE`, concurrent transition and idempotency checks, tenant
isolation, signed-field mutation attacks, journal verification, restart
durability and backup/restore equality. The qualification artifact is retained
by GitHub Actions run `36119356688`.

This boundary qualifies the release transition transaction and its persistence
guarantees in staging-equivalent infrastructure. It does not qualify managed
production infrastructure, external KMS custody, customer data, production
dispatch or the Institution Compiler worker.

### Priority 1: Managed staging

Configure cloud account, remote state, certificate, OIDC and secrets; run Terraform/TFLint/Checkov; review IAM and cost; apply through protected approval; run migration and qualification.

### Priority 2: Authoritative Institution Compiler slice

```text
Source ingestion
→ classification
→ extraction
→ IR mapping
→ deterministic validation
→ Control Graph diff
→ simulation
→ authorized review
→ KMS-signed release
→ shadow deployment
→ immutable receipt
```

Start with one facility, one workflow and one decision boundary. Do not compile an entire enterprise at once.

### Priority 3: Connect the Command Center

Add browser API client and OIDC session; replace operational fixtures; implement loading, stale, unauthorized, restricted, unavailable and failure states; retain simulation labels where appropriate.

### Priority 4: C1 runtime integration

Deploy a qualified shadow release behind the Intelligence API; bind calls to Institution Pack/state/evidence/releases; enforce timeout, schema and abstention; record invocation receipts.

### Priority 5: First connector and paid shadow pilot

Select one measurable workflow, use read-only data, run historical replay, operate in shadow, compare recommendations with outcomes, produce defensible value evidence and expand only after bounded proof.

## 31. Canonical glossary

| Term | Definition |
| --- | --- |
| Cerebrum | Complete institutional intelligence platform |
| C1 | EDON learned institutional-reasoning model |
| Kernel | Independent deterministic authority and policy evaluator |
| Institution Builder | UI for candidate institutional representations |
| Institution Compiler | Server-only deterministic compiler service |
| Institutional IR | Canonical machine-readable institution representation |
| Institution Pack | Versioned IR, graph, policy, workflow and qualification release |
| Domain Pack | Domain semantics, schemas, validators and workflows |
| Control Graph | Versioned entities, relationships, dependencies and control |
| Institutional State | Versioned state projected from admitted evidence |
| Evidence | Typed record supporting, disputing or qualifying state |
| Commitment | Promise, obligation, reservation or deadline |
| Mandate | Time- and scope-bounded actor authority |
| Proposal | Typed plan from C1 or authorized planner |
| Decision Context | Exact state, evidence, policy, authority and release bindings |
| Receipt | Hash-bound signed lifecycle record |
| Reconstruction | Deterministic point-in-time replay |
| Shadow Mode | Evaluation mode with no production dispatch capability |
| Execution Assurance | Boundary converting authorization into governed commands |
| ActionNet | Training and evaluation corpus for institutional reasoning |
| Qualified Release | Release passing declared gates for a specific scope |
| Verified Value | Value supported by governed outcome evidence |

## 32. Instructions for AI builders

Before modifying Cerebrum:

1. Read this document completely.
2. Identify affected layers and lifecycles.
3. Inspect contracts and validated server behavior.
4. Preserve every applicable invariant.
5. Do not infer production readiness from UI presence.
6. Do not move authoritative behavior into browser code.
7. Do not grant C1 authority or credentials.
8. Do not merge compilation with activation.
9. Do not bypass Kernel, human review or Execution Assurance.
10. Do not weaken tenant isolation, custody or receipt binding.
11. Update documentation, status and tests in the same change.
12. State when infrastructure, credentials or external validation are unavailable.

Required implementation report:

```text
Implemented
Validated
Not validated
Still simulated
Production blockers
Capability status after change
```

Forbidden claims:

- Production-ready because it builds.
- Authoritative because it has a UI.
- Secure because labels display authentication.
- Durable because memory tests pass.
- Tenant-isolated without API and RLS attack tests.
- Signed without custody verification.
- Verified when only observed, reported or inferred.
- Executed when evaluated only in shadow.

## 33. Document maintenance

At each material milestone update `last_updated`, `version`, implementation status, readiness gates and terminology; verify UI labels match runtime truth.

Versioning:

- Patch: clarification without behavior change.
- Minor: new layer, lifecycle capability or material status change.
- Major: incompatible architecture or doctrine change.

## 34. Closing statement

Cerebrum is not only a model and not only a dashboard. Institution Builder and Compiler define a versioned institution. Observation and evidence establish admissible information. State projection and the Control Graph maintain context. C1 understands, diagnoses, plans and proposes. The Kernel evaluates authority. Humans govern. Execution Assurance controls action. Outcome services verify results. Receipts and reconstruction preserve proof. ActionNet and release controls turn verified experience into future qualified intelligence.

The platform succeeds only when intelligence, authority, execution and proof remain separate but interoperable.
