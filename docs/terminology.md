# Terminology

| Term | Definition |
| --- | --- |
| Institution Compiler | Provenance-preserving source-to-candidate-IR pipeline |
| Institutional IR | Typed canonical representation of institutional mechanisms |
| Cerebrum platform | Horizontal institutional-intelligence platform defined by `CEREBRUM-PLATFORM-VISION-002`; the complete target is not yet implemented |
| Experience layer | Command Center, embedded decision cards, APIs, SDKs, webhooks, and governed agent access to the same Control Plane |
| Command Center | Human operating interface for incidents, plans, evidence, approvals, execution, governance, and value measurement |
| Intelligence API | Versioned institutional-task API for observations, assessments, plans, simulations, proposals, execution requests, state, and audit; not a generic chat or authorization API |
| Control Plane | Custodian and orchestrator for institutional state, commitments, objectives, incidents, resources, policy versions, and audit lineage |
| Institutional Control Graph | Versioned computational representation of actors, systems, evidence, state, policy, authority, commitments, resources, plans, actions, receipts, and outcomes; service-owned records remain governed by their lifecycle services |
| Identity and Capability Registry | Registry of who or what exists and what it can technically perform; capability never implies permission |
| Delegated Authority and Commitment Layer | Control Plane services for identity/capability, mandates, commitments, reservations, decision receipts, and compensation |
| Mandate | Signed, scoped, time-bound, revocable delegation from an accountable grantor; evidence for Kernel evaluation, not an action authorization by itself |
| Commitment Ledger | Versioned custody of institutional promises, owners, beneficiaries, dependencies, deadlines, breach, fulfillment, and discharge |
| Resource Reservation System | Lifecycle service for temporary or committed resource holds; reservation does not authorize resource consumption |
| Reasoning Runtime | Model-neutral runtime that routes assessment, planning, simulation, optimization, uncertainty, and proposal work across qualified models and solvers |
| Model and Solver Registry | Deployment-controlled inventory of qualified models, solvers, simulators, critics, perception services, and communication components with explicit identities, schemas, permissions, capability envelopes, evaluations, budgets, fallbacks, and rollback targets |
| Enforceable routing policy | Versioned deterministic eligibility, permission, budget, and fallback rules selecting only currently deployed qualified components; learned routers may advise but do not enforce eligibility |
| Routing decision | Auditable selection record containing requested capability, candidates, checks, selected component, fallback sequence, expected cost/latency, and routing-policy version |
| Invocation receipt | Content-bound record of one component call, including identity, input/output hashes, evidence, grant, tools, cost, latency, validation, fallback, result, and trace |
| Data-access grant | Purpose-bound, minimized, expiring, tenant- and jurisdiction-scoped permission for a specific intelligence component; non-transitive and independently revocable |
| Runtime budget | Registered cost, latency, retry, tool-call, context, concurrency, and degradation limits for intelligence routing |
| Action proposal | Exact, version-bound, non-binding proposed action with evidence, consequences, uncertainty, preconditions, resources, and lineage |
| Institutional Environment Gateway | Umbrella integration boundary for agents, systems, resources, observations, authorized-action delivery, and outcomes |
| Observation and Connector Gateway | Target platform name for the governed evidence-ingress and authorized connector-interaction boundary; the current Institutional Environment Gateway is a partial reference predecessor |
| Environment event | Non-authoritative, time-gated evidence about an agent, system, resource, state change, action receipt, or outcome |
| Agent Gateway | Agent-facing protocol and custody component of the Institutional Environment Gateway |
| Cerebrum System | Complete non-authoritative institutional-intelligence architecture containing C1, state/world/memory, planning, optimization interfaces, coordination, prediction, and provenance |
| C1 | Learned-model layer inside the Cerebrum System; historical experiments called this component Cerebrum |
| Institutional State Engine | Deterministic versioned state service that keeps epistemic, authority, execution, and outcome dimensions separate; the existing five-view engine is a v1 reference predecessor |
| Epistemic state | Evidentiary status such as unknown, reported, observed, inferred, disputed, or verified |
| Authority state | Status of Kernel consideration such as unassessed, approval required, authorized, denied, expired, or revoked |
| Execution state | Operational lifecycle such as reserved, dispatched, acknowledged, partial, completed, failed, cancelled, or compensated |
| Outcome state | Status of downstream effects such as unknown, reported, observed, verified, contested, or failed |
| Observed state | State supported by a registered direct observation, without implying authorization or commitment |
| Reported state | State asserted by a registered actor or system, without silently promoting the report to truth |
| Inferred state | Model-derived state carrying explicit model lineage and uncertainty |
| Authorized state | State or mutation covered by a separate authorization record but not necessarily committed |
| Committed state | Versioned state durably recorded through the deterministic commit boundary |
| Causal/provenance graph | Horizontal append-only lineage with explicit evidence status; not causal proof by itself |
| ActionNet | System that generates, captures, and qualifies governed institutional experience and content-bound training releases |
| ActionNet Experience and Learning Contract | Mature custody contract separating observations, interpretations, simulations, human judgments, proposals, decisions, executions, verified outcomes, corrections, and counterfactuals while governing rights and permitted learning uses |
| Evaluation and Release Registry | Signed custody of artifacts, evaluations, qualified workflows, limitations, capability envelopes, canary limits, and rollback targets; registry inclusion does not deploy a release |
| Deployment Controller | Independent service that verifies release signatures, compatibility, approval, scope, attestation, monitoring, containment, canary, and rollback before installation |
| Execution Assurance | Service that revalidates an exact Kernel authorization against current state, reserves resources, dispatches through approved connectors, reconciles outcomes, and compensates when required |
| Decision Receipt | Immutable content-bound proof of the proposal, graph and policy versions, evidence, mandate, checks, and Kernel result |
| Execution Receipt | Immutable lifecycle proof of validation, reservation, dispatch, acknowledgement, partial effects, outcome evidence, and terminal execution status |
| Compensation Manager | Recovery service for partial or failed execution; every consequential recovery action requires a new proposal and Kernel decision |
| Domain pack | Versioned domain-specific IR extensions, connector mappings, Kernel policies, solvers, actions, evaluations, capability envelope, and operator views |
| First Qualified Operational Workflow | First bounded customer workflow used to qualify the complete platform path; it does not permanently define Cerebrum's industry |
| Institutional memory | Tenant-local context used without changing C1 weights |
| Local ActionNet | Tenant-isolated ledger containing one institution's governed experience |
| Global ActionNet | Registry of approved normalized abstractions with rights, privacy, source, and permitted-use custody; not a raw centralized data lake |
| C1 version | Immutable offline-trained model generation such as C1-v1 or C1-v2 |
| C2 | Reserved name for a future architectural successor, not an ordinary retraining checkpoint |
| Latent institutional coordination | Causal coordination mediated through institutional state without a required direct message chain |
| Coordination hypothesis | Non-binding C1/Cerebrum System output describing detection, participants, causal path, forecast, uncertainty, and governance recommendation |
| Institutional resilience | Ability of an institution to preserve authorized objectives and critical functions, enter safe degraded modes, and recover under disruption; currently an EDON research direction, not an established capability |
| Resilience hypothesis | Non-binding analysis of a possible anomaly, cascade, compromised state, affected objectives, forecast, and candidate containment or recovery response |
| EventNet | Deterministic event-queue transition and evaluation environment |
| Kernel | Independent deterministic authorization-decision boundary. The current exact-request token and world-commit path is a reference predecessor; target execution belongs to Execution Assurance |
| Pivotal pair | Intervention pair whose disposition must change |
| Invariance pair | Representation change whose disposition must remain stable |
| Contextual pair | Non-decisive change dominated by another condition |
| Protected evaluation | Hidden-label evaluation separated from prediction runtime |
| Binding authority | Legal/operational ability to commit institutional state |
| Claim gate | Frozen evidence requirements for a specific scientific statement |
