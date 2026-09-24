# EDON

EDON is a research and engineering platform for building Cerebrum: a horizontal
institutional-intelligence platform that connects existing systems, maintains
typed institutional state, produces governed proposals, preserves human
authority, and learns only through reviewed evidence and controlled releases.

> **Research status:** EDON supports bounded synthetic representation, execution,
> learning, and repair claims. It has not established real-institution transfer,
> production safety, autonomous authority, or a validated Institution Foundation
> Model.

## Architecture

```text
Humans + applications -> Command Center / Cards / Intelligence API
                                      |
                                      v
                    Institutional Control Graph
                                      |
                                      v
        Reasoning Runtime -> Exact Action Proposal
                                      |
                   Delegated Authority + Commitments
                                      |
                              Independent Kernel
                                      |
                         Execution Assurance + Recovery
                                                |
                                                v
                               Observation + Connector Gateway
                                                |
                               ERP / WMS / MES / EHR / agents / robots
                                                |
                                      outcomes + audit
                                                v
                   Reviewed ActionNet -> Release Registry
                                                |
                                      Deployment Controller
                                                |
                                      Reasoning Runtime
```

EDON treats the changing institution—not an individual model or agent—as the
unit of intelligence. The Control Graph represents it; Cerebrum reasons over
it; mandates define delegated authority; the Kernel authorizes exact proposals;
Execution Assurance acts and verifies; receipts preserve proof; outcomes update
the graph; and the Deployment Controller governs later releases.

The frozen target architecture is
[`CEREBRUM-PLATFORM-VISION-002`](docs/architecture/cerebrum-platform-vision-002.md).
Its status is `FROZEN_CONTROLLING_VISION_NOT_IMPLEMENTED`. The repository's
implemented reference components are described separately below.

The controlling product and technical-contract map is
The vendor-neutral implementation foundation is
[`CEREBRUM-PLATFORM-FOUNDATION-001`](docs/implementation/cerebrum-platform-foundation-001.md).
Its status is `DRAFT_IMPLEMENTATION_SPECIFICATION_NOT_DEPLOYMENT_AUTHORIZATION`.
The proposed first cloud mapping is
[`CEREBRUM-AWS-DEPLOYMENT-PROFILE-001`](docs/deployment/cerebrum-aws-deployment-profile-001.md),
with status `DRAFT_REFERENCE_DEPLOYMENT_NOT_PRODUCTION_QUALIFIED`. The AWS
profile is replaceable and does not make the frozen platform architecture
cloud-specific.

### Architecture freeze and next priority

`CEREBRUM-MATURE-PLATFORM-SPEC-001` is frozen as **Cerebrum Mature Platform
Specification v1.0**. Routine architectural expansion stops at this boundary.
New ideas belong in a backlog; a successor specification should be created only
when implementation, evaluation, or customer evidence exposes a genuine
structural conflict or missing safety boundary. This freeze establishes the
controlling design, not evidence that the design has been implemented or that
its capabilities have been demonstrated.

The next product milestone is the **First Qualified Operational Workflow**:
one bounded workflow with a design partner, predefined value and safety gates,
and an end-to-end historical-replay and read-only shadow path:

```text
Validated evidence admission
→ versioned state projection and Control Graph update
→ assessment and alternative plans
→ exact action proposal
→ independent Kernel decision
→ human review when required
→ decision receipt
→ observed-outcome comparison and audit
```

Multi-domain expansion, broad connector coverage, and consequential autonomous
execution remain later stages. They should follow evidence from the first
qualified workflow rather than precede it.
[`CEREBRUM-MATURE-PLATFORM-SPEC-001`](docs/architecture/cerebrum-mature-platform-spec-001.md).
Its status is `FROZEN_CONTROLLING_PRODUCT_SPECIFICATION_NOT_IMPLEMENTED`.

### Architecture freeze and next priority

`CEREBRUM-MATURE-PLATFORM-SPEC-001` is frozen as **Cerebrum Mature Platform
Specification v1.0**. Routine architectural expansion stops at this boundary.
New ideas belong in a backlog; a successor specification should be created only
when implementation, evaluation, or customer evidence exposes a genuine
structural conflict or missing safety boundary. This freeze establishes the
controlling design, not evidence that the design has been implemented or that
its capabilities have been demonstrated.

The next product milestone is the **First Qualified Operational Workflow**:
one bounded workflow with a design partner, predefined value and safety gates,
and an end-to-end historical-replay and read-only shadow path:

```text
Validated evidence admission
→ versioned state projection and Control Graph update
→ assessment and alternative plans
→ exact action proposal
→ independent Kernel decision
→ human review when required
→ decision receipt
→ observed-outcome comparison and audit
```

Multi-domain expansion, broad connector coverage, and consequential autonomous
execution remain later stages. They should follow evidence from the first
qualified workflow rather than precede it.

The compiler reconciles three distinct evidence layers without silently treating
observed behavior as legitimate policy:

```text
Normative sources ─┐
Operational state ─┼─> conflict-preserving candidate IR ─> authorized review
Behavioral traces ─┘
```

## Repository map

| Path | Purpose |
| --- | --- |
| `docs/` | Architecture, terminology, roadmap, claims, reproducibility, and IP-process documentation |
| `docs/implementation/` | Vendor-neutral implementation foundations beneath the frozen architecture |
| `docs/deployment/` | Replaceable cloud and private deployment profiles |
| `docs/specifications/` | Eleven canonical specifications, including model routing and ActionNet learning custody |
| `papers/` | Publication source locations and shared bibliography |
| `src/edon/` | Compiler, IR, ActionNet, Cerebrum, runtime, provenance, and safety packages |
| `product/cerebrum-platform/` | Unified target product boundary and implementation-readiness package |
| `product/actionnet-platform/` | Downloadable ActionNet product documentation, configuration, security, and readiness package |
| `product/actionnet-learning-network/` | Local-to-global experience promotion, offline releases, and frozen C1 version custody |
| `product/cerebrum-system/` | Cerebrum System component boundaries, C1 lifecycle, and internal reference status |
| `product/agent-gateway/` | Vendor-neutral agent-integration architecture, API, security, vendor matrix, and readiness package |
| `product/institutional-environment-gateway/` | Umbrella architecture for agent, system, resource, observation, authorized-action, and outcome integration |
| `schemas/` | Machine-readable contracts |
| `experiments/` | Self-contained experiment records and the canonical registry |
| `evaluations/` | Metrics, scorers, safety analyses, and frozen gates |
| `benchmarks/` | GovBench, EventNet, and diagnostic fixtures |
| `models/` | Configuration and manifest records; no large weights in Git |
| `provenance/` | Dataset, model, experiment, source, and approval lineage |
| `governance/` | Claim, IGI-scope, IP, risk, review, and release-gate records |
| `results/` | Small frozen summaries and artifact manifests |
| `examples/` | Bounded example institution packages |

## Quick start

No third-party runtime dependencies are required for the repository validator.

```bash
PYTHONPATH=src python -m edon.cli validate .
python -m unittest discover -s tests -v
```

Run the complete synthetic platform demonstration:

```bash
PYTHONPATH=src python examples/demo/run_demo.py --output-dir /tmp/edon-demo
```

Run the authenticated API and dashboard:

```bash
export EDON_API_KEYS='{"replace-with-a-long-admin-token":"ADMIN"}'
PYTHONPATH=src python -m edon.cli serve --state-dir var/edon
```

Open `http://127.0.0.1:8080/` and enter the configured token.

## Current implemented reference path

```text
Sources → Compiler → Review Registry → Approved IR → Runtime/Kernel
                                   ↘ ActionNet → Qualification → frozen C1
Observations → World + Memory → Goals → Plans → Resources/Agents → Outcomes/Replans
Cerebrum System/C1 → Typed Proposal → Shadow Supervisor → Kernel Token → World Commit → Outbox
Local Worlds → Redacted Projections → Hierarchical Federation → Escalation / Solver Candidate
External Agents → MCP/A2A/REST/FHIR → Agent Gateway → Shadow Proposals → Kernel Boundary
Agents/Systems/Resources → Environment Gateway → State Engine → Cerebrum System → Kernel → Outcomes → ActionNet
Institution memory → context-only adaptation; Local ActionNet → governed Global ActionNet → offline C1-vNext
Adversarial evidence → separated state → resilience hypothesis → Kernel-governed response
```

The current reference implementation includes immutable review provenance, high-risk dual approval,
versioned promotion and rollback, deterministic execution, synthetic experience
generation, qualification gates, seed orchestration, shadow comparisons, gap
discovery, persistent event-sourced institutional state, governed episodic
memory, typed observations, dynamic goals, validated long-horizon plans,
resource allocation, multi-agent coordination, outcome monitoring, corrective
replanning, review-gated learning candidates, an authenticated API, dashboard,
exact-request Kernel tokens, replay protection, a transactional outbox, a typed
Cerebrum operations adapter, durable shadow supervision, the EDON-OPS-002
integration gate, Docker deployment, and CI.
The additive EDON-FED-001 reference also provides immutable hierarchical scopes,
multilevel aggregate state, least-common-ancestor escalation, and a validated
non-binding capacity-allocation provider boundary.

The additive Agent Gateway core provides tenant-bound MCP, A2A, REST/webhook,
and read-only FHIR R4/SMART normalization; immutable message custody;
idempotency and replay protection; allowlisted connector profiles; and
content-minimized OpenTelemetry-compatible spans. It includes configuration
profiles for eleven enterprise-agent and healthcare platforms, but no native
vendor connector is yet production-certified. Ingress remains shadow-only and
egress is staged without delivery.

The broader Institutional Environment Gateway architecture places the Agent
Gateway inside a common boundary for agents, systems, and resources. It defines
time-gated environment events, a separate Kernel-authorized action path, and an
ActionNet outcome loop. This umbrella is partially implemented through existing
world, operations, Kernel, outbox, ActionNet, and Agent Gateway components;
native enterprise-system/resource adapters and authorized delivery workers do
not yet exist.

The additive `CEREBRUM-BUILD-001` engineering lane provides an opt-in local C1
Qwen plus LoRA operations provider behind the existing typed proposal adapter,
immutable shadow custody, and Kernel boundary. The deterministic provider
remains the default. No Build-001 model has been trained or benchmarked.

`CEREBRUM-CLOSED-LOOP-DEV-001` now materializes the corresponding development
curriculum: 288 synthetic training episodes, 2,496 supervised decisions, 72
held-out development episodes, and an executable fail-closed environment for
goal creation, planning, capability/resource dispatch, monitoring, recovery,
verification, and safe termination. No learned closed-loop result exists yet.

## Cerebrum System and C1

The target platform division is:

- **The Control Plane maintains institutionally governed state and coordination.**
- **The Institutional Control Graph represents the institution under a versioned decision clock.**
- **The Reasoning Runtime, including C1 where qualified, proposes and simulates.**
- **Identity, capability, mandate, commitment, and reservation services provide governed authority evidence.**
- **Humans create or approve scoped mandates only within their own authority.**
- **The independent Kernel authorizes exact proposals.**
- **Execution Assurance validates, acts, verifies, and invokes separately authorized recovery.**
- **Decision and execution receipts preserve why and what occurred.**
- **The Model and Solver Registry and enforceable routing policy constrain every intelligence provider.**
- **ActionNet preserves reviewed experience without directly training or deploying production models.**
- **ActionNet captures reviewed experience; the Release Registry and Deployment
  Controller govern later runtime releases.**

The existing Cerebrum System reference combines C1 with deterministic, time-gated state views;
world and memory services; planning and independently validated optimization;
coordination and prediction; and horizontal causal/provenance lineage. Observed,
reported, inferred, authorized, and committed state remain separate.

C1 is the architectural name for the learned component historically called
“Cerebrum” in EDON experiments. Historical experiment IDs, artifacts, results,
and claims retain their original terminology. See
[`docs/architecture/cerebrum-terminology-migration.md`](docs/architecture/cerebrum-terminology-migration.md).

## Memory and governed learning

Memory and learning are separate. Institutional memory gives a frozen C1
version immediate tenant-specific context without changing its weights. Local
ActionNet records what happened inside one institution. Only reviewed,
non-protected, de-identified, rights-bound abstractions may cross into Global
ActionNet, and global training releases remain offline-only and do not
themselves authorize a weight update.

Future retrains use versioned names such as `C1-v1` and `C1-v2`; `C2` is
reserved for an architectural successor. See
[`docs/architecture/memory-learning-actionnet.md`](docs/architecture/memory-learning-actionnet.md).

## Institutional resilience research direction

EDON's proposed resilience role is not to “beat ASI.” It is to study whether a
non-authoritative institutional-intelligence layer can identify cross-system
manipulation, unsafe cascades, poisoned state, resource exhaustion, and latent
coordination quickly enough to support safe containment and recovery while
Kernel and accountable humans retain binding authority.

This direction is complementary to cybersecurity and incident response. It is
currently an architecture and research agenda, not a validated defense or
national-security capability. See
[`docs/architecture/institutional-resilience.md`](docs/architecture/institutional-resilience.md).

## Bounded institutional-intelligence scope

[`EDON-IGI-SCOPE-001`](governance/igi-scope/EDON-IGI-SCOPE-001/README.md)
freezes the first finite environment class for future bounded general
institutional-intelligence evaluation. It defines three nested profiles,
mechanism and task families, variation axes, compute/adaptation caps, safety
invariants, transfer requirements, exclusions, and evidence tiers.

The scope passes 42/42 definition-integrity controls. This means the definition
is frozen and internally consistent; it does not mean Cerebrum covers the scope.
Transfer-008 is mapped only to the EventNet Core task slice.

## IP and publication governance

[`IP_GOVERNANCE.md`](IP_GOVERNANCE.md) and [`docs/ip/`](docs/ip/README.md)
provide EDON's sanitized invention-harvesting, filing-before-publication,
trade-secret, trademark, copyright, ownership, data-rights, and counsel-handoff
process. Machine-readable fail-closed status is maintained under
[`governance/ip/`](governance/ip/README.md).

No application or registration is represented as filed by these documents.
Candidate invention families remain subject to professional patentability,
inventorship, ownership, eligibility, prior-art, and freedom-to-operate review.
Confidential disclosures, legal advice, assignments, actual trade-secret values,
and protected benchmark contents must remain outside Git.

```bash
python scripts/release/validate_ip_governance.py
```

IP status never upgrades EDON's scientific claims. “Patent pending,” registered
trademark symbols, and bounded-IGI proof language remain unauthorized unless
their independent legal and scientific gates are satisfied.

## ActionNet Platform product

`ACTIONNET-PLATFORM-002` packages ActionNet as a governed institutional-
experience product rather than only an experiment generator. It includes a
versioned mechanism atlas, evidence-graded composition edges, an immutable
experience ledger, procedural/adversarial world blueprints, protected-vault
custody, independent review dimensions, model-exposure records, registered
coverage, acquisition recommendations, non-binding interventions, and
content-bound training releases. The additive Platform 002 upgrade provides a
canonical Institutional IR, explicit temporal and epistemic state, executable
mechanism composition, replay-verified counterfactual generation, bounded
human-behavior scenarios, and locally minimized governed abstraction intake.

The Platform 001 workflow passes 18/18 internal gates and the Platform 002
active-experience workflow passes 26/26 internal gates.

The product API is included in the standard EDON service. See
`product/actionnet-platform/README.md`. The current status is an internal MVP,
not production authorization.

This is an integrated internal MVP. It is not yet externally security-audited,
validated on real institutions, connected to production identity systems, or
authorized to make binding decisions.

The source tree contains an allowlisted, hash-verified migration from the
preserved research archive. Large or protected artifacts remain outside this
Git-facing layer and are represented by manifests.

## Agent Gateway product

[`product/agent-gateway/`](product/agent-gateway/README.md) defines the common
integration boundary for OpenAI, AWS, Microsoft, Google, Anthropic, Salesforce,
ServiceNow, UiPath, LangGraph, Epic, Oracle Health, and custom agents. Universal
paths are MCP, A2A, REST/webhooks, OpenTelemetry, and read-only FHIR R4/SMART.

Current status is `INTERNAL_PROTOCOL_CORE_NOT_PRODUCTION_AUTHORIZED`. The
normalization, custody, tenant, replay, audit, and authority-separation controls
are implemented. Live vendor clients, production identity and secrets,
OAuth/SMART lifecycle, webhook signatures, outbound delivery, managed telemetry,
external security review, and vendor/customer conformance remain required.

## Institutional Environment Gateway

[`product/institutional-environment-gateway/`](product/institutional-environment-gateway/README.md)
defines the broader integration target around the current Agent Gateway. It
models `AGENT`, `SYSTEM`, and `RESOURCE` entities; preserves occurrence,
observation, and controller-availability times; separates untrusted observation
from Kernel-authorized action delivery; and routes verified state changes and
outcomes into governed ActionNet experience candidates.

Current status is
`ARCHITECTURE_DEFINED_PARTIALLY_IMPLEMENTED_NOT_PRODUCTION_AUTHORIZED`. The
architecture and non-authoritative environment-event contract exist, but no
live ERP, CRM, EHR, inventory, finance, facilities, robotics, or generalized
resource adapter is claimed.

## Current research status

| ID | Purpose | Status | Bounded result |
| --- | --- | --- | --- |
| `CEREBRUM-DEV-001` | Initial learned development test | Completed | Counterfactual training signal; safety hold |
| `CEREBRUM-DEV-002` | Multi-task safety repair | Passed | Both registered seeds pass internal synthetic gates |
| `CEREBRUM-TRANSFER-003` | Independent-implementation transfer | Failed gate | Partial signal; transfer not established |
| `CEREBRUM-DEV-004` | Structured transition/queue repair | Completed; narrow hold | Seed 1 passed; seed 2 passed 16/17 and missed unresolved-appeal behavior |
| `ACTIONNET-DATA-QUAL-006` | Appeal-boundary narrow-repair data | Qualified | 35/35 controls; balanced resolved/unresolved appeal cases |
| `ACTIONNET-DATA-QUAL-007` | Execution-transfer repair data | Qualified | 37/37 controls; fresh queue, transition, and pair lineage |
| `ACTIONNET-DATA-QUAL-008` | Governed multi-domain authoring world | Ready for expert authoring | 42/42 controls; 24 domain packs; zero training-eligible records |
| `CEREBRUM-DEV-006` | Appeal-boundary learned repair | Ready to execute | Two registered seeds and 20-check gates; no learned result yet |
| `CEREBRUM-TRANSFER-005` | Fresh generalization test | Frozen; unauthorized | Cannot be reused after DEV-004 failed its two-seed gate |
| `CEREBRUM-TRANSFER-006-EXPLORATORY` | Pre-repair transfer diagnostic | Ready to execute | Fresh 560-case label-free runtime; no prediction or score yet |
| `CEREBRUM-DEV-009-RB1` | Compute-bounded cross-profile repair | Completed; failed gate | Strong certificate, transition, and pair signal; queue and unresolved-appeal safety gates failed |
| `CEREBRUM-DEV-010` | Queue-integrity and appeal repair | Completed; failed gate | Seed 1 passed; seed 2 failed unresolved-appeal and zero-unsafe gates |
| `ACTIONNET-DATA-QUAL-011` | Focused unresolved-appeal repair data | Qualified | 27/27 controls; 768 train and 64 validation certificates |
| `CEREBRUM-DEV-011-FOCUSED` | Two-parent failure-only continuation | First run completed; focused hold | Zero unsafe and 32/32 unresolved, but 30/32 resolved appeals missed the 95% floor |
| `ACTIONNET-DATA-QUAL-012` | Balanced appeal-finality calibration data | Qualified | 28/28 controls; 384 train and 64 validation certificates |
| `CEREBRUM-DEV-012-FOCUSED` | Short balance continuation | Completed; focused hold | 59/64 final decisions and one unsafe authorization; safe checkpoint 12 retained for diagnosis |
| `ACTIONNET-DATA-QUAL-013` | Tight near-clock selection and confirmation data | Qualified | 29/29 controls; exact clock-minus-one/clock-plus-one pairs across three disjoint splits |
| `CEREBRUM-DEV-013-FOCUSED` | Safety-constrained checkpoint selection | Focused signal | Step 6 selected; confirmation 63/64 with zero unsafe and 9/9 checks |
| `ACTIONNET-DATA-QUAL-014` | Fresh full multi-task regression data | Qualified | 31/31 controls; 192 records, 48 per task, no training split |
| `CEREBRUM-DEV-014-FULL` | Selected-candidate full regression | Completed; hold | 16/26 checks; zero unsafe but transition and queue-state reconstruction failed |
| `ACTIONNET-DATA-QUAL-015` | Mixed replay and retention-regression data | Qualified | 37/37 controls; 384 train, 64 development, and 192 confirmation records |
| `CEREBRUM-DEV-015-MIXED` | Mixed multi-task retention repair | Completed; development hold | Both checkpoints passed 23/26; confirmation remained sealed |
| `ACTIONNET-DATA-QUAL-016` | Delayed-evidence and exact-state repair data | Qualified | 33/33 controls; 368 train, 64 development, and 192 confirmation records |
| `CEREBRUM-DEV-016-NARROW` | Narrow safety and state repair | Completed; development hold | Both checkpoints 23/26 with the same 12 failures; confirmation sealed |
| `ACTIONNET-DATA-QUAL-017` | Complete-exposure causal-chain repair data | Qualified | 37/37 controls; 384 train, 64 development, and 192 confirmation records |
| `CEREBRUM-DEV-017-CAUSAL` | Full-exposure causal-chain continuation | Completed; development hold | Both checkpoints passed 18/26, retained two unsafe authorizations, and left confirmation sealed |
| `ACTIONNET-DATA-QUAL-018` | Verified-hybrid evaluation data | Qualified | 33/33 controls; zero train, 64 development, and 192 single-use confirmation records |
| `CEREBRUM-DEV-018-VERIFIED` | Frozen model with deterministic execution and verification | Verified hybrid synthetic signal | 209/256 model outputs accepted; all hybrid confirmation checks passed with zero unsafe output |
| `CEREBRUM-DEV-019-DIAGNOSTIC` | Cumulative gold-intervention localization | Completed; instrument-validity hold | Raw 27/32 decisions; event-order support caused 11 decision degradations, preventing unique localization |
| `ACTIONNET-DATA-QUAL-020` | Direct interface-calibration data | Qualified | 31/31 controls; 64 calibration and 64 disjoint heldout scenarios; no training split |
| `CEREBRUM-DEV-020-INTERFACE-CALIBRATION` | Representation equivalence and decision fidelity | Ready pending external lineage | 21/21 core controls; 384 calibration predictions and conditional 192-prediction heldout stage |
| `CEREBRUM-TRANSFER-010` | Independent-authorship EventNet successor reservation | Closed unmaterialized | DEV-010 failed its frozen prerequisite; no protected artifacts |
| `CEREBRUM-BUILD-001` | Engineering-first learned provider | Shell ready; execution not run | Local Qwen/LoRA C1 provider and matched benchmark design; no trained model or performance result |
| `CEREBRUM-CLOSED-LOOP-DEV-001` | Learned closed-loop development environment | Ready for two-seed training | 288 training episodes and 72 held-out development episodes; deterministic reference passes, but no learned result exists |

See [`experiments/README.md`](experiments/README.md) for the full registry and
evidence boundaries.

The complete executable ActionNet simulation lineage (`DATA-QUAL-001` through
the current focused successors) is included under `experiments/`, with generated synthetic
corpora, lineage, schedulers/oracles, qualification reports, checksums, and tests.
ActionNet-008 extends the runtime-loadable world with governed multi-domain
authoring, expert routing, feedback contracts, and training gates. Its current
records are source-ungrounded and `training_eligible=false`; protected future
families and real institutional data remain outside the repository by design.

```bash
python scripts/data/rebuild_actionnet_world.py --verify-only
```

## Reproducing major results

Every major experiment package must contain:

- `README.md`: purpose, inputs, execution, and status;
- `PROTOCOL.md`: frozen methodology, conditions, metrics, and gates;
- `CLAIMS.md`: supported, unsupported, provisional, and known limitations;
- `manifest.json`: artifact identities, hashes, lineage, storage, and claim scope.

Large weights, protected labels, raw institutional data, secrets, and temporary
outputs are excluded from Git. Their manifests remain versioned.

## Claim traceability

The required trace is:

```text
paper claim
  -> governance/claim-registry/claims.json
  -> experiment ID
  -> experiment manifest
  -> dataset/model/config/scorer identities
  -> frozen result hash
```

A missing link blocks the claim from release.

## Papers

Publication folders live under `papers/`. The current dissertation source,
submission records, and frozen PDF are under `papers/ifm/`; the migration ledger
is recorded in `migration/inventory.json`.

## Contributing and security

Read [`CONTRIBUTING.md`](CONTRIBUTING.md), [`SECURITY.md`](SECURITY.md),
[`IP_GOVERNANCE.md`](IP_GOVERNANCE.md), and
[`docs/claim-boundaries.md`](docs/claim-boundaries.md) before changing evidence,
schemas, runtime authority, publication scope, or release gates.

## License

No public-use license has been granted yet. See [`LICENSE.md`](LICENSE.md).