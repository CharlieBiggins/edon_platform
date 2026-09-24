# Platform operations

This document describes the current internal reference service. The controlling
target architecture is `CEREBRUM-PLATFORM-VISION-002`. Existing `/api/*` routes
are not the future public `/v1` contract and must not be represented as a
production Intelligence API.

The controlling product contract map is
`CEREBRUM-MATURE-PLATFORM-SPEC-001`. The current service does not implement its
Model and Solver Registry, enforceable routing policy, purpose-bound data
grants, invocation receipts, runtime budgets, or mature ActionNet learning
contract.

The vendor-neutral implementation requirements are drafted in
`CEREBRUM-PLATFORM-FOUNDATION-001`. The proposed initial AWS mapping is
`CEREBRUM-AWS-DEPLOYMENT-PROFILE-001`. Both records remain unqualified drafts;
they describe required boundaries and possible services rather than deployed
infrastructure or production readiness.

## Target public boundary

The future public interface uses institutional resources: observations,
incidents, assessments, plans, simulations, action proposals, Kernel decision
reads, authorization-bound execution requests, commitments, institutional
state, and audit records. No public endpoint allows a caller to issue an
authorization. `/api/kernel/tokens` remains an internal reference endpoint and
must not be exposed as the target product interface.

## Control-plane roles

| Role | Permissions |
| --- | --- |
| `VIEWER` | Read status, candidates, mechanisms, and audit events |
| `COMPILER_OPERATOR` | Compile, simulate, and generate ActionNet data |
| `REVIEWER` | Submit candidate reviews and conflict resolutions |
| `DOMAIN_REVIEWER` | Provide the domain approval required for high-risk promotion |
| `SAFETY_REVIEWER` | Provide the independent safety approval required for high-risk promotion |
| `EXECUTIVE_RISK_OWNER` | Provide the third approval required for critical-risk promotion |
| `RELEASE_MANAGER` | Promote and roll back mechanism versions |
| `SHADOW_OPERATOR` | Submit shadow comparisons and request gap proposals |
| `KERNEL_AUTHORIZER` | Issue short-lived exact-request Kernel execution tokens |
| `KERNEL_COMMITTER` | Commit token-bound world creation and events |
| `FEDERATION_OPERATOR` | Register hierarchy, publish redacted projections, route decisions, and manage escalations |
| `OPTIMIZATION_OPERATOR` | Request validated non-binding optimization candidates |
| `GATEWAY_ADMIN` | Register, review, enable/suspend, and audit tenant agent connectors |
| `GATEWAY_OPERATOR` | Read gateway records, ingest messages, and stage non-delivered egress |
| `GATEWAY_INGRESS` | Submit tenant-bound gateway ingress only |
| `ACTIONNET_AUTHOR` | Author mechanisms, compositions, worlds, and non-protected experiences |
| `ACTIONNET_DOMAIN_REVIEWER` | Review ActionNet domain validity |
| `ACTIONNET_SAFETY_REVIEWER` | Independently review ActionNet safety |
| `ACTIONNET_PRIVACY_REVIEWER` | Review governed real-world abstractions for privacy |
| `ACTIONNET_CUSTODIAN` | Control protected records, overlap checks, exposure, quarantine, and audit |
| `ACTIONNET_RELEASE_MANAGER` | Review training use, approve eligibility, and freeze releases |
| `ACTIONNET_CURRICULUM_OPERATOR` | Freeze coverage and create acquisition recommendations |
| `ACTIONNET_INTERVENTION_OPERATOR` | Create non-binding intervention candidates |
| `ACTIONNET_INTAKE_OPERATOR` | Submit locally minimized governed abstractions; cannot approve their privacy or training use |
| `ACTIONNET_GLOBAL_CUSTODIAN` | Promote qualified local abstractions and freeze Global ActionNet releases |
| `C1_RELEASE_MANAGER` | Register frozen C1 versions and evidence-backed non-operational dispositions |
| `WORLD_OPERATOR` | Maintain world state, governed memory, and the internal operations loop |
| `OPERATIONS_OPERATOR` | Ingest observations and operate goals, plans, resources, agents, outcomes, and monitoring |
| `ADMIN` | All internal MVP permissions |

Configure roles as a JSON token map in `EDON_API_KEYS`. Tokens must contain at
least sixteen characters; production deployments require stronger randomly
generated secrets and TLS. Reviewer and promoter identities are derived from the
authenticated token rather than accepted from request bodies.

ActionNet product principals may optionally be tenant bound:

```json
{
  "long-random-token": {
    "role": "ACTIONNET_AUTHOR",
    "tenant_id": "institution-a"
  }
}
```

The service rejects requests that attempt to cross the authenticated tenant.

## Data custody

- compiler source bundles are stored under the configured state directory;
- registry decisions and audit hashes are transactional SQLite records;
- public ActionNet inputs and protected oracle labels use separate artifacts;
- seed predictions are frozen by content hash;
- shadow and gap reports remain non-authoritative;
- no endpoint commits an external institutional action.

## Institutional continuity

- world state is tenant-isolated, version-bound, event-sourced, and replayable;
- every world mutation requires an explicit authorization reference;
- stale expected versions fail closed;
- restoration appends a new event instead of rewriting history;
- episodic memories carry sensitivity, retention, source events, provenance,
  and content hashes;
- memory reads and queries create immutable tenant-specific audit events;
- tombstoned and expired memories are excluded from ordinary retrieval.

The secure Kernel endpoints validate internal exact-request execution tokens.
Legacy reference operations still accept recorded authorization references, so
production deployment must route every binding operation through the secure
commit path.

## Governed operations

The operations API supports:

- `/api/operations/bootstrap`, `/api/operations/state`, and initialization of
  existing event-sourced worlds;
- `/api/observations`, `/api/agents`, `/api/agent-status`, and `/api/resources`;
- `/api/goals`, `/api/goal-transitions`, `/api/plans`, and `/api/replans`;
- `/api/ready-steps` and `/api/assignment-proposals` for non-binding scheduling;
- `/api/resource-allocations`, `/api/step-assignments`, and atomic
  `/api/dispatches`;
- `/api/step-starts`, `/api/step-outcomes`, `/api/step-cancellations`, and
  monitoring endpoints.

Outcome records cannot claim verified success when required expected outcomes
are absent. Failures block the goal, mark the plan `NEEDS_REPLAN`, create an
alert, and produce a non-training-eligible learning candidate. Robot and service
commands remain proposals with `binding_authority=false`.

## Secure commit and supervision

- `/api/whoami` returns the authenticated role and actor identity used for token
  binding;
- `/api/kernel/tokens` is restricted to `KERNEL_AUTHORIZER` or `ADMIN`;
- `/api/kernel/worlds` and `/api/kernel/world-events` require a matching token
  and `KERNEL_COMMITTER` or `ADMIN` role;
- `/api/supervisor/cycles` records a version-pinned, non-binding shadow cycle;
- every world event writes a transactional outbox message with token hash,
  mutation, lineage, and resulting-state custody.

### Optional local C1 model

The default shadow provider is deterministic. An exploratory local Qwen base
plus optional LoRA may be enabled with:

```bash
export EDON_C1_PROVIDER=qwen
export EDON_C1_MODEL=Qwen/Qwen3-4B-Instruct-2507
export EDON_C1_ADAPTER=/persistent/models/cerebrum-build-001/final-adapter
export EDON_C1_MODEL_LINEAGE=cerebrum-build-001:replace-with-frozen-hash
export EDON_C1_LOAD_IN_4BIT=1
```

Optional controls include `EDON_C1_MAX_INPUT_TOKENS`,
`EDON_C1_MAX_NEW_TOKENS`, and `EDON_C1_LOCAL_FILES_ONLY`. Historical
`EDON_CEREBRUM_*` names remain accepted as compatibility aliases. The model
stack is loaded on the first shadow cycle. Malformed or unavailable generation
produces an abstention; authority-bearing output is rejected. Neither path falls
through to execution.

The reference `CerebrumSystem` composes the C1 adapter with a deterministic
five-view state projector and append-only causal/provenance graph. This
reference cycle remains non-binding and does not request a Kernel token.

## Hierarchical federation and optimization

- `/api/federation/scopes` registers immutable global, domain, regional,
  facility, and edge scopes;
- `/api/federation/projections` emits a version-bound redacted local summary;
- `/api/federation/aggregates` composes child summaries and may publish the
  aggregate to an ancestor;
- `/api/federation/routes` computes local handling or the required escalation
  target from affected scopes, impact, uncertainty, and authority;
- `/api/federation/escalation-events` preserves acknowledgement and resolution
  as additive records;
- `/api/optimization/candidates` validates capacity-allocation proposals and
  always returns `binding_authority=false`.

These endpoints coordinate proposals and summaries. They do not grant a global
model permission to write local state or bypass an institution-local Kernel.

## Agent Gateway

The `/api/gateway/` namespace provides tenant-bound MCP, A2A, REST/webhook, and
read-only FHIR R4/SMART normalization. Connectors start disabled and need a
security-review reference plus a managed-secret reference before enablement.
Accepted ingress is `ACCEPTED_SHADOW_ONLY`; egress is
`STAGED_NOT_DELIVERED`. Messages and audit events are immutable and replay
protected. OTLP-compatible spans omit message content by default.

Vendor profiles are configuration guidance only. The repository does not yet
contain live vendor clients, OAuth/SMART exchanges, webhook signature profiles,
outbound delivery workers, or production conformance results. Operational and
security requirements are in `product/agent-gateway/`.

## Institutional Environment Gateway

The Agent Gateway is one adapter family within the broader Institutional
Environment Gateway. The umbrella architecture treats agents, systems, and
resources as distinct typed entities and captures observations, availability or
capacity changes, state changes, action receipts, and outcomes with separate
occurrence, observation, and controller-availability timestamps.

The general event contract is non-authoritative. It cannot carry a raw Kernel
token or claim that its record executed an action. Authorized outbound behavior
must originate from the Kernel and transactional outbox, then pass through a
target-specific adapter that preserves request, delivery, acknowledgement, and
reconciliation lineage. Those generalized system/resource adapters and
delivery workers are not implemented by the current repository.

## ActionNet Platform

The `/api/actionnet-platform/` namespace provides canonical Institutional IR,
registered and executable composition, replay-verified counterfactual branches,
explicit temporal/epistemic state, bounded human-behavior scenarios, locally
minimized governed abstraction intake, procedural worlds, experience custody,
role-bound reviews, protected overlap,
quarantine, model exposure, coverage, acquisition, intervention, audit, training
eligibility, and release workflows. Protected records are hidden from ordinary
queries and cannot be used for training. Real governed abstractions require an
additional privacy approval.

Use `scripts/actionnet/backup_platform.py`, `verify_backup.py`, and
`readiness.py` for local backup and operational checks. These tools do not
replace production database, disaster recovery, security, and compliance
controls.

## ActionNet learning network

`/api/actionnet-network/promotions` accepts a tenant-local experience only after
the existing ActionNet review, overlap, and eligibility gates pass. The payload
must be a de-identified normalized abstraction with rights, privacy, source
review, and permitted-use hashes. `/api/actionnet-network/releases` revalidates
the local source and freezes an offline-only release.

`/api/c1/versions` registers immutable `C1-vN` lineage. It rejects online and
institution-specific weight updates. `/api/c1/dispositions` records
evidence-gated eligibility or rollback metadata with
`operational_effect=false`; it does not load a model or change production
traffic.

## Institutional resilience direction

No resilience detector, containment endpoint, or national-security operating
mode is enabled by the current service. Existing state, provenance, gateway,
supervisor, Kernel, outbox, and ActionNet records are foundations for future
evaluation only.

Any future anomaly or cascade hypothesis must remain non-binding. Containment,
isolation, resource denial, configuration rollback, or emergency reallocation
requires a separately approved Kernel policy, a registered blast radius,
required human review, expiry, rollback or compensating action, and an auditable
outcome. Operators must retain deterministic or manual degraded modes when C1,
Cerebrum, a gateway, or an evidence source is unavailable or suspected to be
compromised.

## Rollback

Promoting a new version deactivates the prior active version without deleting it.
A release manager can reactivate a preserved version, producing a new audit-chain
event. Rollback does not rewrite historical reviews, promotions, or artifacts.

## Required work before production

- implement and qualify the Control Plane, multidimensional state model,
  Execution Assurance, Release Registry, Deployment Controller, runtime
  monitoring, and bounded Command Center;
- implement the Institutional Control Graph plus identity/capability, mandate,
  commitment, reservation, decision-receipt, and compensation lifecycles;
- implement deployment-controlled model/solver registration, enforceable
  routing, invocation receipts, data grants, budgets, and qualified fallback;
- isolate a proposal- and authorization-bound Credential Broker from the
  Reasoning Runtime, Control Plane, Kernel, Execution Assurance identity, and
  customer connectors;
- admit connector outcomes through validation and evidence projection rather
  than allowing direct institutional-state mutation;
- implement independently verifiable authoritative receipt custody separately
  from sampled operational telemetry;
- implement a versioned `/v1` facade and migration policy without weakening the
  current fail-closed internal routes;
- select, register, replay, shadow, and qualify a First Qualified Operational
  Workflow under explicit customer permissions and claim boundaries;
- external identity provider, TLS, token rotation, and signed approvals;
- database backup, recovery, migration, and high-availability testing;
- measure the proposed pilot SLOs and replace planning cost envelopes with a
  dated workload-specific infrastructure bill of materials;
- connector-specific privacy and authorization controls;
- native system and resource adapters with identifier, unit, clock, and state
  reconciliation contracts;
- production message broker integration, dead-letter operations, and
  cross-service memory projection;
- vendor-specific MCP/A2A/FHIR conformance, OAuth/SMART lifecycle, webhook
  signatures, outbound gateway delivery, and reconciliation;
- replicated regional planes, cross-scope transport, consistency policy, and
  distributed authorization custody;
- reviewed operations-research, forecasting, routing, and scheduling providers;
- approved perception models, semantic indexes, and hardware/service adapters;
- rate limiting, structured logs, metrics export, and incident automation;
- independent security and source-validity audits;
- protected real-institution validation and operational authorization.