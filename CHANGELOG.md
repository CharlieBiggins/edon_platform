# Changelog

## 0.13.0 — 2026-09-23

- Registered `CEREBRUM-PLATFORM-FOUNDATION-001` as a vendor-neutral draft
  implementation specification beneath the unchanged frozen mature platform
  architecture.
- Defined logical services, six initial deployables, PostgreSQL-first custody,
  proposal-bound credential isolation, authoritative receipts, independent
  deployment governance, proposed pilot SLOs, and fourteen evidence-based
  freeze gates.
- Registered `CEREBRUM-AWS-DEPLOYMENT-PROFILE-001` as a replaceable,
  unqualified AWS mapping using managed services, ECS Fargate for CPU services,
  qualified non-Fargate GPU paths, RDS PostgreSQL, S3/Object Lock,
  EventBridge/SQS, Step Functions, and explicit account and credential
  boundaries.
- Updated repository, product, readiness, governance, and manifest entry points
  without modifying the frozen platform vision, mature specification, or any
  historical experiment.

## 0.12.0 — 2026-09-22

- Froze `CEREBRUM-MATURE-PLATFORM-SPEC-001` as the controlling mature product
  and technical-contract map layered on unchanged Vision-002.
- Expanded the platform from nine to eleven canonical specifications by adding
  Model Routing and Intelligence Runtime plus ActionNet Experience and Learning.
- Added six target contracts for component registration, routing decisions,
  invocation receipts, purpose-bound data grants, runtime budgets, and mature
  ActionNet trajectory/rights/learning custody.
- Standardized the seven Kernel decisions, retained expiration as reason codes,
  preserved evidence-versus-truth separation, and registered zero observed
  unauthorized committed actions as an evaluation gate rather than a population
  guarantee.
- Updated mutable repository, product, schema, terminology, claim, roadmap,
  operations, governance, and readiness entry points without modifying either
  frozen platform vision or any historical experiment.

## 0.11.0 — 2026-09-21

- Preserved the hash-frozen `CEREBRUM-PLATFORM-VISION-001` predecessor and
  added `CEREBRUM-PLATFORM-VISION-002` as the controlling additive successor.
- Added the Institutional Control Graph, Delegated Authority and Commitment
  Layer, and Decision/Execution/Compensation Receipt specifications.
- Added target contracts for graph nodes, edges, and snapshots; identity and
  capability; mandates; commitments; resource reservations; decision receipts;
  execution receipts; and compensation records.
- Clarified that capability does not imply authority, human approval requires
  Kernel reevaluation, compensation requires new authorization, and the
  Evaluation and Release Registry cannot update the Reasoning Runtime without
  the Deployment Controller.
- Updated the platform package and mutable architecture, terminology, claim,
  roadmap, operations, schema, and product entry points without modifying
  historical experiments or Vision-001's frozen logical content.

## 0.10.0 — 2026-09-20

- Froze `CEREBRUM-PLATFORM-VISION-001` as the controlling horizontal Cerebrum
  architecture with an explicit not-implemented, not-production-authorized
  claim boundary.
- Added six canonical specifications covering the Event Envelope,
  multidimensional Institutional State Model, Institutional IR lifecycle,
  action lifecycle, release/deployment contract, and First Qualified
  Operational Workflow.
- Added twelve additive JSON contracts for events, state, IR governance,
  proposals, Kernel decisions, authorization-bound execution, Execution
  Assurance, releases, deployment approval, runtime attestation, domain packs,
  and workflow qualification.
- Added a unified `product/cerebrum-platform/` package, architecture preflight,
  content inventory, and regression tests while preserving all historical
  experiments, results, hashes, C1 identities, and internal `/api/*` contracts.
- Updated the repository overview, terminology, claim boundaries, research
  roadmap, platform operations, and component architecture documents to
  distinguish the target platform from current reference implementations.

## 0.9.13 — 2026-09-07

- Froze the DEV-019 result as procedurally complete but insufficient for unique
  causal localization: raw decisions were correct on 27/32 scenarios, while
  the cumulative event-order condition caused 11 decision and 15 exact
  degradations.
- Added a reproducible implementation audit showing that DEV-019 nested raw,
  typed, ordered, and executed-state descriptions, grew mean prompts from
  3,773.75 to 9,185.63 characters, retained a queue-recomputation task, and did
  not make the supplied decision immutable.
- Added `ACTIONNET-DATA-QUAL-020`, a 31/31-control, zero-training source with 64
  calibration and 64 disjoint heldout scenarios across five direct
  single-source representations and an authenticated decision-fidelity arm.
- Added `CEREBRUM-DEV-020-INTERFACE-CALIBRATION`, which automatically selects
  at most one representation under paired noninferiority, preservation, and
  safety gates before opening a 192-prediction heldout stage.

## 0.9.12 — 2026-09-06

- Froze the completed `CEREBRUM-DEV-018-VERIFIED` result: the model was
  accepted on 209/256 cases, 47 outputs were overridden, and 13 unsafe model
  paths were blocked. Model-only confirmation passed 22/26 checks with four
  unsafe authorizations; the verified hybrid passed 26/26 with zero unsafe.
- Added `ACTIONNET-DATA-QUAL-019`, a 34/34-control repeated-measures diagnostic
  matrix containing 32 fresh scenarios under five cumulative gold
  interventions and no training split.
- Added `CEREBRUM-DEV-019-DIAGNOSTIC`, a zero-training evaluation of raw input,
  typed events, canonical order, predecision state, and gold decision. Paired
  recovery identifies an earliest demonstrated failure stage without claiming
  unique causal identification.

## 0.9.11 — 2026-09-06

- Froze `CEREBRUM-DEV-017-CAUSAL` as a negative result: checkpoints 12 and 24
  each passed 18/26 full-regression checks, retained two unsafe
  authorizations, shared 13 failing cases, and left confirmation sealed.
- Added `ACTIONNET-DATA-QUAL-018`, a zero-training, 33/33-control source with
  64 fresh development and 192 single-use confirmation records.
- Added `CEREBRUM-DEV-018-VERIFIED`, which keeps DEV-017 checkpoint 24 only as
  a frozen engineering model, independently executes every observation with a
  target-blind deterministic engine, and fails closed on any mismatch.
- Registered separate model-only and verified-hybrid metrics, per-case
  acceptance/override audits, explicit unsafe-`ALLOW` override counts, and the
  unchanged all-26-check development gate. Transfer remains unauthorized.

## 0.9.10 — 2026-09-06

- Preserved the operator-reported `CEREBRUM-DEV-016-NARROW` negative result:
  both checkpoints passed 23/26 checks, shared all 12 failing cases, retained
  one delayed-evidence unsafe authorization, and left confirmation sealed.
- Added `ACTIONNET-DATA-QUAL-017`: 384 fresh records from 48 pivotal pairs,
  with complete queue--state--decision--certificate/pair supervision across
  the five observed failure mechanisms; all 37 controls pass.
- Added `CEREBRUM-DEV-017-CAUSAL`: a 24-step continuation from the clean
  DEV-015 checkpoint 12. Effective batch 16 yields exactly 384 registered
  sample exposures, one complete pass over the 384-record curriculum.
- Registered checkpoints 12 and 24, a fresh 64-case all-26-check development
  gate, and a new conditional 192-case confirmation. Transfer remains locked.

## 0.9.9 — 2026-09-06

- Preserved the operator-reported `CEREBRUM-DEV-015-MIXED` development hold:
  both checkpoints passed 23/26 frozen checks and produced identical aggregate
  metrics. Queue exactness improved from 6.25% to 75%, transition exactness
  from 22.92% to 81.25%, and transition post-state exactness from 25% to
  87.5%, but each checkpoint made one delayed-evidence unsafe authorization,
  scored 5/6 on pivotal certificates, and reconstructed 14/16 transition
  post-states. The 192-case confirmation remained sealed.
- Added `ACTIONNET-DATA-QUAL-016`: 368 entirely fresh delayed-evidence and
  exact-state repair records, 64 fresh development-selection records, and 192
  new single-use confirmation records; all 33 controls pass.
- Added `CEREBRUM-DEV-016-NARROW`: a 12-step, learning-rate-1e-6 continuation
  from DEV-015 checkpoint 12, with checkpoints at 6 and 12, automatic
  field-level parent auditing, all-26-check development selection, and a new
  sealed confirmation.
- DEV-014 and DEV-015 validation cases remain excluded from training;
  transfer and seed-reproducibility authorization remain false.

## 0.9.8 — 2026-09-05

- Preserved the operator-reported `CEREBRUM-DEV-014-FULL` negative result:
  16/26 checks passed with zero unsafe authorizations, but transition exactness
  fell to 22.92%, queue exactness to 6.25%, unresolved appeals to 1/2, and one
  transition reached its generation limit.
- Added a field-level DEV-014 audit tool and froze the parent, input, and
  prediction identities without importing raw GPU artifacts.
- Added `ACTIONNET-DATA-QUAL-015`: 384 mixed replay records emphasizing
  transition and queue trace, 64 fresh development-selection records, and 192
  single-use full-confirmation records; all 37 controls pass.
- Added `CEREBRUM-DEV-015-MIXED`: a 24-step, learning-rate-3e-6 continuation
  from the safe DEV-013 step-6 adapter. Checkpoints 12 and 24 must pass all 26
  checks on development before the untouched confirmation can open.
- Transfer and seed-reproducibility authorization remain false.

## 0.9.7 — 2026-09-05

- Preserved the operator-reported `CEREBRUM-DEV-013-FOCUSED` result: step 6
  and step 12 both scored 32/32 on development, the registered earlier-step
  tie-break selected step 6, and untouched confirmation scored 63/64 with
  zero unsafe authorizations and all 9 focused checks passing.
- Added `ACTIONNET-DATA-QUAL-014`, a fresh 192-case held-renderer regression
  with 48 certificate, transition, queue-trace, and pair-contrast records;
  all 31 qualification controls pass and no training split exists.
- Added `CEREBRUM-DEV-014-FULL`, which freezes the selected step-6 adapter,
  performs zero optimizer steps, and applies the original 26-check full gate.
  Seed reproducibility and transfer remain unauthorized.

## 0.9.6 — 2026-09-05

- Preserved the operator-reported `CEREBRUM-DEV-012-FOCUSED` negative result:
  the final checkpoint scored 59/64 with 28/32 resolved and 31/32 unresolved
  appeals but introduced one unsafe authorization.
- Recorded the same-instrument learning curve: the DEV-011 parent scored 38/64,
  DEV-012 checkpoint 12 scored 54/64 with zero unsafe authorizations, and the
  final checkpoint scored 59/64 with one unsafe authorization. All final
  errors were exactly one tick from the decision clock.
- Added `ACTIONNET-DATA-QUAL-013`, with 192 training, 32 adaptive
  development-selection, and 64 single-use confirmation certificates under
  exact clock-minus-one versus clock-plus-one appeal pairs; 29/29 controls
  pass.
- Added `CEREBRUM-DEV-013-FOCUSED`, a 12-step continuation from the safe
  DEV-012 checkpoint 12 with checkpoints at 6 and 12, three-candidate
  safety-first development selection, untouched confirmation, resumable
  predictions, and 30/30 core readiness controls.
- Kept full regression, transfer authorization, production authority, and
  binding execution false.

## 0.9.5 — 2026-09-05

- Preserved the operator-reported first `CEREBRUM-DEV-011-FOCUSED` run. It
  passed 8/9 gates with 32/32 unresolved appeals and zero unsafe
  authorizations, but two resolved appeals remained conservatively
  `CONTESTED`, leaving resolved-ALLOW accuracy at 30/32 against the 95% floor.
- Applied the registered compute-saving early stop before the second parent.
- Added `ACTIONNET-DATA-QUAL-012`: 384 symmetrically weighted balanced training
  certificates, 64 fresh held-renderer validation certificates, disjoint
  families/renderers/cases, and 28/28 qualification controls.
- Added `CEREBRUM-DEV-012-FOCUSED`, a 24-step, lower-learning-rate continuation
  from the exact DEV-011 seed-26090512 adapter, with checkpoints every 12 steps,
  resumable prediction, immediate scoring, and 22/22 core readiness controls.
- Kept the 95% floors and zero-unsafe requirement unchanged. Full regression
  and transfer authorization remain false.

## 0.9.4 — 2026-09-05

- Preserved the operator-reported `CEREBRUM-DEV-010` negative result. Seed
  26090401 passed 26/26 gates; seed 26090402 passed 24/26, failed both fresh
  unresolved-appeal certificates, and made one unsafe `ALLOW`.
- Added `ACTIONNET-DATA-QUAL-011`, a fresh failure-focused corpus with 768
  training and 64 held-renderer validation certificates, balanced resolved
  `ALLOW` and unresolved `CONTESTED` cases, and 27/27 qualification controls.
- Added `CEREBRUM-DEV-011-FOCUSED`, which continues both frozen DEV-010 LoRA
  adapters for 48 optimizer steps each, checkpoints 64 predictions per parent,
  and requires both runs to meet strict appeal-boundary and zero-unsafe gates.
- Kept full regression and Transfer-010 authorization explicitly false. A
  focused pass can authorize only a separately identified confirmation run.

## 0.9.3 — 2026-09-04

- Added `CEREBRUM-TRANSFER-010`, a fresh blocked transfer successor identity
  for possible passing DEV-010 candidates without reopening Transfer-008.
- Reserved 192 label-free records from 48 pairs across four governance forms,
  while leaving exact cases, prompts, seeds, renderers, labels, generator,
  oracle, runtime, predictions, scorer, and score unmaterialized.
- Required independent protected authorship, a separately implemented
  generator and oracle, a distinct custodian, prohibited-overlap commitments,
  and a frozen power analysis before materialization.
- Added raw, interface-matched, and prompted Qwen conditions, two strong
  frontier-model slots from distinct providers, an optional RB1 repair-effect
  diagnostic, and a transparent rules ceiling.
- Limited the primary claim to DEV-010-trained EventNet capabilities and
  explicitly excluded raw-source compilation, gold-versus-compiled IR,
  explicit UNREPRESENTABLE output, learned closed-loop operation, and mini-IGI.
- Added fail-closed candidate and baseline registration, materialization
  authorization, six schemas, 55 passing shell controls, and nine focused
  tests. No transfer result is created.

## 0.9.2 — 2026-09-04

- Imported and hash-verified the completed `CEREBRUM-DEV-009-RB1` two-seed
  result. Both seeds froze all 192 predictions, but the registered summary
  passed only 4/6 checks and froze `RB1_TRANSFER_NOT_ESTABLISHED`.
- Localized the common failure to one high-confidence unresolved-appeal unsafe
  authorization in both seeds and 22 shared queue-trace failures dominated by
  noncanonical or incomplete event ordering and deferred-list partitioning.
- Added `ACTIONNET-DATA-QUAL-010`: 4,032 fresh training records, 192 disjoint
  held-renderer validation records, explicit queue-order and queue-partition
  supervision, 33/33 qualification controls, and five focused tests.
- Added executable `CEREBRUM-DEV-010` two-seed QLoRA training, resumable
  prediction, locked scoring, a 26-check per-seed gate, 24/24 readiness
  controls, and six focused tests. No learned DEV-010 result exists.
- Closed Transfer-008 materialization under its frozen identity because its RB1
  prerequisite failed. Any future pass must use a newly identified transfer
  and capstone successor rather than substituting adapters into frozen shells.

## 0.9.1 — 2026-09-03

- Added `CEREBRUM-CLOSED-LOOP-DEV-001`, a materialized development-only
  interactive environment for learned goal formation, planning,
  capability/resource dispatch, outcome monitoring, failure recovery,
  verification, and safe termination.
- Generated 288 training episodes in 144 counterfactual pairs, 2,496 supervised
  training turns, 72 held-out development episodes in 36 pairs, and 624
  label-separated validation turns across disjoint institutional profiles and
  renderers.
- Added a deterministic Kernel-shaped commit boundary that rejects authority
  fields and incorrect proposals without mutating state, plus eight-cycle
  success and ten-cycle replanning paths.
- Registered two-seed interactive advancement gates, a development training
  release, schemas, reference replay, 28 generation controls, 22 readiness
  controls, and six focused tests. Added the package to the capstone's
  prohibited-reuse inventory. No learned closed-loop, Transfer-008,
  capstone, real-institution, production, or IGI result is claimed. Seven
  focused tests cover replay, separation, no-hindsight release, label custody,
  authority rejection, and incorrect dispatch.

## 0.9.0 — 2026-09-02

- Added `CEREBRUM-MINI-IGI-CAPSTONE-001`, the minimum internal bounded-IGI
  conjunction test for frozen unseen-institution transfer and learned
  closed-loop operation under Kernel-only commit authority.
- Reserved 72 protected episodes and 36 counterfactual pairs across regional
  health operations, municipal utility restoration, and federated research
  governance, with structurally distinct authority topologies and isolated
  author roles.
- Covered all thirteen Scope-001 task families, eighteen mechanism families,
  and fourteen variation axes within smaller Coordinated Operations bounds.
- Registered nine matched controller conditions, C1-only component ablations,
  two-seed reproducibility, per-institution floors, zero-unsafe hard gates, and
  one frozen score transaction.
- Added schemas, a 58-control fail-closed preflight, twelve focused tests, and
  claim/roadmap integration. RB1, Transfer-008, and a two-seed learned
  closed-loop result remain prerequisites; no protected instrument,
  predictions, score, bounded-IGI result, external validation, production
  authority, or binding authority exists.

## 0.8.2 — 2026-09-01

- Added a pre-materialization Transfer-008 baseline-fairness amendment without
  changing the original Scope-001-hash-anchored manifest, reservation, or gate
  bytes.
- Retained raw unmodified Qwen as an end-to-end diagnostic and added
  interface-matched and prompted interface-matched Qwen conditions under the
  same model revision, observations, token limits, schema constraint,
  deterministic compiler, hardware class, case order, and zero-retry policy as
  the C1 candidates.
- Made the stronger eligible matched Qwen condition the primary learned
  comparator and required separate raw-validity, conditional-reasoning,
  compiled-output, safety, execution, token, and retry reporting.
- Added a frozen baseline contract, pre-RB1 baseline registry, custody
  commitments, materialization checks, and focused shell tests. No RB1,
  Transfer-008, model-superiority, or transfer result is created by this
  amendment.

## 0.8.1 — 2026-08-30

- Added a bounded institutional-resilience architecture and threat model for
  state poisoning, cross-system cascades, latent coordination, authority
  confusion, temporal manipulation, resource exhaustion, compromised
  components, and provenance suppression.
- Defined the proposed detect--reconstruct--forecast--propose--authorize--recover
  loop while retaining Kernel and accountable humans as the only binding
  authority path.
- Added source diversity, uncertainty, no-hindsight, least-privilege blast
  radius, degraded-operation, rollback, and offline-learning invariants.
- Registered a staged evidence path from synthetic institutional ranges through
  independent red teams and shadow studies. No ASI-defense,
  critical-infrastructure, adversary-resistance, government-affiliation, or
  national-security capability claim is made.
- Added dated U.S. policy context from primary White House sources as background
  only; policy relevance does not validate EDON.

## 0.8.0 — 2026-08-30

- Separated institution-local memory from model learning. Memory now reports
  `INSTITUTION_LOCAL`, `CONTEXT_ONLY`, `training_eligible=false`, and
  `weight_update_authorized=false`.
- Added `GovernedLearningNetwork`, preserving the tenant ActionNet ledger as
  the local eligibility authority while admitting only reviewed,
  overlap-checked, non-protected, de-identified, rights-bound abstractions into
  Global ActionNet.
- Added global release-time revalidation of the local source, offline-only
  training releases, protected-evaluation reservations, and immutable C1 model
  generation records using the `C1-vN` convention.
- Added evidence-gated C1 shadow/deployment-eligibility, rollback, revocation,
  and archive dispositions. These records have no operational effect and never
  authorize weight loading, traffic changes, or institutional execution.
- Added API roles and routes, schemas, learning governance, product/security
  documentation, and nine focused fail-closed tests. No real institution has
  contributed data, no model has been trained through the network, and no
  federated-learning, performance, transfer, production, or IGI claim is made.

## 0.7.0 — 2026-08-30

- Defined Cerebrum as the complete non-authoritative institutional-intelligence
  system and C1 as its learned-model layer, while preserving every historical
  `CEREBRUM-*` identity, artifact, metric, claim, and compatibility interface.
- Added a deterministic State Engine that keeps observed, reported, inferred,
  authorized, and committed state separate under a controller-availability
  clock, including explicit same-time conflicts and content-bound idempotency.
- Added an append-only causal/provenance graph spanning source, state, C1
  inference, planning, optimization, authorization, commit, outcome, artifact,
  and ActionNet experience records without treating recorded lineage as causal
  proof.
- Added a non-binding Cerebrum System reference cycle, C1 adapter and
  `EDON_C1_*` configuration names, with historical `EDON_CEREBRUM_*` aliases.
- Added public state, C1 manifest, system-cycle, and provenance schemas;
  architecture migration governance; a product package; and nine focused tests.
  No trained C1 artifact, full-system performance result, transfer result,
  production authorization, or binding authority is claimed.

## 0.6.0 — 2026-08-30

- Added the Institutional Environment Gateway as the umbrella architecture for
  agents, systems, resources, observations, Kernel-authorized actions, state
  changes, outcomes, and governed ActionNet experience.
- Added explicit time-gated environment-event contracts while preserving the
  existing Agent Gateway as the implemented agent-facing protocol component.
- Defined separate observation, Kernel-authorized action, and governed
  experience paths so connectors cannot manufacture execution authority or
  silently turn operational events into training data.
- Added `CEREBRUM-LATENT-COORD-001`, a separate protected research shell for
  detecting, attributing, reconstructing, predicting, and governing coordination
  mediated through institutional state rather than direct messages.
- Added Cerebrum coordination-state and non-binding hypothesis schemas covering
  communications, actions, artifacts, mutations, resource flows, queues,
  schedules, configuration changes, causal dependencies, lineage, forecasts,
  uncertainty, and governance recommendations.
- Registered four matched controller conditions, 480 reserved cases, 240 causal
  pairs, eight balanced coordination modes, two-seed gates, no-hindsight timing,
  protected custody, single-score controls, and a 35/35 shell preflight.
- Added a product architecture package, production-readiness checklist,
  fail-closed status manifests, research/IP integration, and automated contract
  checks. Native enterprise-system/resource adapters, authorized delivery
  workers, detector, protected instrument, causal validation, predictions,
  scores, and real-institution results remain unbuilt.

## 0.5.1 — 2026-08-29

- Restored and deterministically rematerialized the complete ActionNet 001–008
  corpora, oracle, lineage, qualification, and checksum chain from the retained
  authoritative sources; all eight package controls and checksum inventories
  verify again.
- Rebuilt ACTIONNET-DATA-QUAL-009's predecessor-overlap reference and complete
  qualified corpus; its twelve local EventNet tests pass.
- Restored the CEREBRUM-PLATFORM-CONTRIB-001 matched training, protected target,
  proxy predictions, freeze, and readiness records. Fixed proxy generation so
  a clean checkout creates its prediction directory before writing artifacts;
  the package returns to 22/22 readiness controls while confirmatory Qwen
  remains correctly blocked.
- Completed the Agent Gateway SQLite custody and service layer behind the
  existing protocol models and API routes, including disabled-by-default
  connectors, review-gated enablement, tenant isolation, immutable message and
  audit records, idempotency rebinding rejection, shadow-only ingress,
  non-delivering egress, telemetry minimization, and capability/vendor views.
- The complete repository suite now passes 69 tests. ActionNet, IP, repository,
  Platform-Contrib, and Agent Gateway validators also pass without changing any
  external, production, transfer, IGI, or binding-authority claim.

## 0.5.0 — 2026-08-29

- Added the vendor-neutral EDON Agent Gateway protocol core for MCP
  `2026-07-28`, A2A `1.0`, REST/webhooks, read-only FHIR R4/SMART, and
  OpenTelemetry-compatible content-minimized traces.
- Added tenant-scoped, disabled-by-default connector profiles with HTTPS,
  secret-reference, security-review, operation/target allowlist, sensitivity,
  idempotency, replay-protection, immutable-custody, and hash-chain controls.
- Added eleven non-certified vendor profiles covering OpenAI, AWS, Microsoft,
  Google, Anthropic, Salesforce, ServiceNow, UiPath, LangGraph, Epic, and Oracle
  Health.
- Added authenticated gateway API roles and routes for connector management,
  ingress, non-delivered egress staging, tenant queries, and audit.
- Preserved the hard execution boundary: gateway payloads cannot carry
  authority, ingress remains shadow-only, and egress is never treated as
  delivered or executed.
- Added schemas, safe example configuration, product/security/readiness
  documentation, and automated protocol, tenancy, replay, audit, and safety
  checks. Native vendor clients and production certification remain unbuilt.

## 0.4.0 — 2026-08-29

- Added a repository-level IP governance entry point and a complete sanitized
  attorney-handoff documentation set covering patent strategy, candidate
  invention families, enablement, prior art, publication controls, trade
  secrets, trademarks, copyright, contracts, data rights, and ownership.
- Registered three initial counsel-review candidates—Institution Compiler/IR,
  ActionNet governed experience, and Cerebrum–Kernel governed operation—plus a
  deferred federation family without asserting novelty, patentability, filing,
  ownership, inventorship, or scientific proof.
- Added fail-closed machine-readable disclosure, trademark, trade-secret,
  rights, and release-review records. No filing, patent-pending status,
  registered mark, completed disclosure inventory, or ownership clearance is
  asserted.
- Added `validate_ip_governance.py` and repository tests to verify public/private
  separation, source anchors, status consistency, and unauthorized-language
  controls.
- Integrated IP review into repository, contribution, security, governance, and
  release documentation while keeping confidential and privileged material out
  of Git.

## 0.3.0 — 2026-08-25

- Added the separate `CEREBRUM-BUILD-001` exploratory engineering lane without
  modifying RB1 or Transfer-008 gates.
- Added an opt-in local Qwen plus optional PEFT/LoRA operations provider with
  lazy GPU imports, deterministic decoding, strict JSON parsing, fail-closed
  abstention for malformed generation, hard authority-field rejection, and
  explicit model-lineage registration.
- Connected learned provider selection to the existing immutable shadow
  supervisor while retaining the deterministic provider as the default.
- Added matched-controller benchmark, training-release, claim-boundary, and
  27-control build-readiness contracts.
- Added `EDON-IGI-SCOPE-001`, a content-hash-frozen finite institutional
  environment definition with three nested profiles, explicit mechanism/task
  families, variation axes, compute caps, safety invariants, transfer rules,
  exclusions, evidence tiers, and 42/42 definition-integrity controls.
- Bound Transfer-008 to the narrow EventNet Core evidence slice without
  modifying the frozen Transfer-008 package or authorizing any IGI claim.

## 0.2.0 — 2026-08-23

- Added ActionNet Platform 002 canonical Institutional IR with explicit mapping
  into `I=(X,E,R,A,P,W,T,C,Sigma)`.
- Added closed object references, seconds-to-months horizons, epistemic state,
  and bounded actor behavior assumptions.
- Added executable mechanism composition with causal ordering, bounded relation
  semantics, horizon snapshots, cycle rejection, and deterministic replay.
- Added active counterfactual generation with parent custody and replay-verified
  child experiences.
- Added locally minimized governed abstraction intake, source-rights and
  redaction attestations, raw-sensitive field rejection, and privacy-gated use.
- Added authenticated API routes, schemas, migration documentation, and the
  26/26-gate `ACTIONNET-PLATFORM-002` evaluation.

## 0.1.0 — 2026-08-14

- Created the GitHub-facing research repository structure.
- Added architecture, claim-boundary, reproducibility, and governance documents.
- Added experiment registry and manifest-only package records.
- Added schema contracts, Python package skeleton, examples, and validation tests.
- Kept protected data, large weights, and unfinished result artifacts outside Git.
- Added the executable Institution Compiler MVP with verified ingestion,
  deterministic extraction, three-layer reconciliation, conflict preservation,
  focused review routing, candidate IR emission, schemas, CLI, example, and
  tests.
- Added the integrated platform MVP: hash-chained review and promotion registry,
  high-risk dual approval, deterministic IR execution, version rollback,
  ActionNet generation, qualification gates, training orchestration, prediction
  freezing, shadow comparison, gap discovery, authenticated API, dashboard,
  Docker/CI infrastructure, and an end-to-end synthetic institution demo.
- Imported and regenerated the complete ActionNet DATA-QUAL-001 through
  DATA-QUAL-005 simulation lineage, including generated corpora, schedulers,
  oracles, lineage, qualification reports, checksums, and original tests.
- Preserved the archived DATA-QUAL-005 result manifest separately and recorded
  its mismatch with the source bytes actually retained in the historical archive.
- Recorded the completed DEV-004 two-seed hold: seed 2 passed 16/17 gates but
  missed the unresolved-appeal mechanism floor.
- Added ACTIONNET-DATA-QUAL-006, a fresh-lineage appeal-boundary repair world
  with 8,064 training records, 1,344 validation records, and 35/35 controls.
- Added the CEREBRUM-DEV-006 executable two-seed protocol; it is ready for GPU
  execution but has no learned result and authorizes no transfer score.
- Added CEREBRUM-TRANSFER-006-EXPLORATORY, a separately identified pre-repair
  transfer protocol with a fresh 560-case label-free runtime. The known DEV-004
  hold is frozen before prediction and confirmatory claims remain disabled.
