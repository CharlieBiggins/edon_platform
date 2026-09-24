# Schemas

Controlling architecture: `CEREBRUM-PLATFORM-VISION-002`  
Controlling product specification: `CEREBRUM-MATURE-PLATFORM-SPEC-001`  
Status: `FROZEN_CONTROLLING_PRODUCT_SPECIFICATION_NOT_IMPLEMENTED`

Schemas define versioned repository contracts. Some describe implemented
internal references; Vision-001 and Vision-002 schemas describe target
architecture and do not establish implemented public APIs, qualified
deployment, production behavior, or binding authority.

The contracts cover institutions, ActionNet cases, Cerebrum System and C1
outputs, runtime proposals, persistent world events and snapshots, governed
episodic memory, operational observations, agents, goals, plans, outcomes, and
provenance manifests. Kernel tokens, transactional outbox messages, Cerebrum
operations proposals, and shadow-supervisor cycles have separate contracts.
Hierarchical federation scopes, redacted projections, routing decisions,
escalations, and non-binding optimization requests/candidates are also
versioned independently.
The ActionNet product contracts separately cover mechanisms, evidence-graded
composition, world blueprints, experience custody, reviews, registered
coverage, acquisition recommendations, intervention candidates, and governed
training releases. Platform 002 adds canonical Institutional IR, executable
composition runs, replay-verified counterfactual batches, explicitly bounded
human-behavior scenarios, and locally minimized governed abstraction intake.
Breaking changes require a new schema version and migration record.

Vision-001 introduced twelve additive target schemas covering:

- `events/event-envelope.schema.json` for immutable, time-gated evidence and
  audit events;
- `institution/institutional-state.schema.json` for separate epistemic,
  authority, execution, and outcome dimensions;
- `institution/ir-lifecycle.schema.json` for governed IR activation and
  supersession;
- `actions/` for proposals, Kernel decisions, authorization-bound execution
  requests, and Execution Assurance records;
- `releases/` for evaluated releases, deployment decisions, and runtime
  attestation;
- `domain-packs/` for bounded deployment semantics; and
- `workflows/` for First Qualified Operational Workflow registration.

These additive contracts specify the target architecture. They do not replace
the existing v1 reference contracts or establish implementation, evaluation,
deployment, or binding authority.

Vision-002 adds ten schemas: `control-graph/` contracts for versioned nodes,
edges, and snapshots; `authority/` contracts for identity/capability, mandates,
commitments, and reservations; and `receipts/` contracts for Kernel decisions,
execution, and compensation. Vision-002 inherits Vision-001's six
specifications and adds three, producing nine canonical specifications in
total. Capability, mandate, authorization, execution, and verified outcome
remain separate states.

The mature product specification adds six contracts: `intelligence/` schemas
for the Model and Solver Registry, routing decisions, invocation receipts,
purpose-bound data grants, and runtime budgets; plus
`actionnet/mature-experience-learning-contract.schema.json` for reviewed
trajectory custody and permitted learning uses. The complete mature platform
contains eleven canonical specifications. Across Vision-001, Vision-002, and
the mature specification, twenty-eight additive target schemas are registered.

The learning-network contracts add tenant-local export custody, de-identified
Global ActionNet abstractions and records, offline-only global training
releases, frozen C1 manifests, and non-binding C1 dispositions. Memory episodes
explicitly remain institution-local, context-only, training-ineligible, and
unable to authorize weight updates.

The `gateway/` contracts cover disabled-by-default connector profiles,
protocol-neutral immutable envelopes, ingress/egress requests, non-binding
receipts, and sanitized vendor capability profiles.

The `environment/` contract defines non-authoritative, time-gated evidence
about `AGENT`, `SYSTEM`, and `RESOURCE` entities. It records occurrence,
observation, and controller-availability times so prospective evaluation cannot
silently use future information. Kernel-authorized commands remain separate
outbox contracts; environment events cannot grant authority or assert execution.

The `cerebrum/` contracts define C1 model lineage, the five-class institutional
state assertion/projection boundary, complete non-binding system cycles, and
latent-coordination state/hypotheses. The `provenance/causal-graph` contract
records horizontal lineage and evidence status without converting sequence or
association into causal proof. None of these contracts grants authority or
records a model proposal as executed.