# CEREBRUM-ACTIONNET-MATCHED-001 — written experiment contract

Version: 0.1.0 draft, September 14, 2026.

Status: **IMPLEMENTED DRAFT — NOT REGISTERED; EXECUTION BLOCKED**.
This document adopts the agreed design decisions. The accompanying framework
implements data preparation, serialization, token planning, registration,
training/prediction dispatch and scoring, but it is not a registration,
completed qualification, GPU-validated runtime, or authorization to spend.
Unresolved commitments in section 10 must be settled before the relevant stage.
No training, inference, protected instrument materialization, or outreach is
launched by this contract. No success is asserted for Program-005.

## 1. Question, scope, and predecessor disposition

Primary question: under a fixed processed-token training budget, does explicit
ActionNet supervision connecting events, state changes, decisions and
counterfactual consequences improve shared operational correctness beyond
ordinary native-program supervision on the same underlying scenarios?

The estimand is the effect of this specified supervision package under the
registered budget and exposure schedule. It is not the effect of every possible
ActionNet implementation, a representation-only ablation, or a universal
institutional-intelligence claim.

First finish and audit Program-005 if the remaining evaluation warrants its
cost; preserve its raw outputs, adapters, hashes, failures and frozen disposition.
Do not retrain it or change its gates. Program-005 has no confirmation stage.
A HOLD is evidence to address explicitly in the new study rationale, not a
success to relabel. Neither a HOLD nor a pass automatically authorizes this study.

`CEREBRUM-ACTIONNET-COMPARISON-001` remains unchanged: an optional five-condition,
48-case, 240-response screen reusing Program-005 adapters, without new training
or token-matching claims. It is not a prerequisite for Matched-001. Record whether
it is run or left unexecuted, with the decision's expected information and cost.
Skipping it does not count as passing it or relaxing its execution gates.

## 2. Arms, starting point, and shared information

The planned four training runs are Ordinary A, ActionNet A, Ordinary B and
ActionNet B. A is exploratory at the screen; B replicates the paired comparison.
Use the same pinned base weights for all four, fresh adapter initialization,
the same adapter architecture and optimizer configuration. Within a seed pair,
share the initialization seed and declared random-stream schedule; use a distinct
declared seed for B. Do not substitute the best of multiple unreported seeds.

The intended starting model is `Qwen/Qwen3-4B-Instruct-2507`, revision
`cdbee75f17c01a7cc42f958dc650907174af0554`, as recorded in Program-003's config.
This is a local design choice, not verification of a downloaded snapshot.
Actual weight, tokenizer, configuration and runtime hashes remain required.
Do not initialize either arm from a Program-003/005 trained adapter: that would
change the starting-point question and requires a revised contract.
Two adapter-training seeds sharing a pretrained base are not independent
end-to-end pretraining lineages.

| Content | Ordinary | ActionNet |
|---|---|---|
| Both members of each counterfactual pair | Yes | Yes |
| Native operational-program targets | Yes | Same targets |
| Required final evaluation output | Same shared schema | Same shared schema |
| Explicit pair relationship and changed-field labels | No | Yes |
| Causal-effect supervision between pair members | No | Yes |
| Intermediate temporal and typed state-transition supervision | No auxiliary targets | Yes |

Both arms receive each member as a standalone scenario. The ordinary arm has no
explicit relational labels, although it may infer relationships from the data.
ActionNet's auxiliary targets must be derived from these same scenarios and the
same reference semantics; they may not introduce exclusive underlying situations.
No auxiliary trajectory or certificate may expose evaluation answers at inference.

The primary output schema must require identical operational fields from both
arms. If an explanation or decision certificate is mandatory, its shared target
is supplied to both. Only ActionNet receives additional causal supervision.
ActionNet-only auxiliary text is not a required field in ordinary primary scoring.
Freeze the serializers, field definitions, reference executor, training templates,
auxiliary loss weights and evaluation parser with valid/invalid examples. This
draft does not pretend these implementations already exist.

## 3. Scenario identity, exposure, and split construction

Freeze a shared scenario inventory with lineage, family, pair and member IDs,
source provenance, canonical inputs, targets and hashes. Each pair is indivisible
for split assignment: no member or related scenario lineage may cross training,
screen or broader evaluation. Exclude known predecessor training/development
exposures and disclosed prior test exposures; report the limits of that audit.
New identifiers alone do not establish novel underlying scenarios.

Before training, audit both serialized datasets against the same inventory.
Require complete shared-pool coverage in each arm's first traversal. If the
budget cannot afford that traversal for either arm, reduce the shared inventory
or revise the budget before registration; do not silently train on different
subsets. Freeze deterministic group order and subsequent traversal rules.

Equal token budgets with longer auxiliary supervision can yield different repeat
counts and optimizer steps. Report realized per-lineage exposure, native target
exposure and auxiliary exposure. Do not claim matched scenario repetition or
matched native-target token exposure unless separately demonstrated.

## 4. Training-token accounting and spending contract

Primary unit: **total processed non-padding training tokens**. Count all non-pad
positions in each consumed training batch, including input and target positions,
whether or not masked from loss, on every actual training traversal. Count a
training example again when it is actually reprocessed. Activation recomputation
inside a step is not another dataset-token exposure; report its compute separately.
Validation and evaluation tokens have separate ledgers, not the training total.

Before registration freeze:

- Tokenizer, chat template and revisions; input, target and total length limits.
- Packing, padding, attention boundaries and position-ID behavior.
- Microbatch, gradient accumulation, effective batch and partial-batch policy.
- Loss masks, normalization and auxiliary weights for each arm.
- Optimizer, learning-rate schedule and its token/step schedule coordinate;
  precision, quantization, adapter modules and checkpoint/resume behavior.
- Per-run token budget, maximum arm-to-arm token difference, tolerance unit,
  group order, and indivisible pair/trajectory-group boundary.
- Per-run and total GPU-hour and currency caps, hardware and stop enforcement.

Proposed stopping policy for registration: stop before a complete group would
exceed the token cap; no overrun and no partial group. Precompute the resulting
totals using the pinned tokenizer for both arms. If coverage or matching tolerance
fails, revise the plan before training. Never silently truncate an overlong target:
resolve or exclude the whole lineage in both arms before the inventory is frozen.

The runner must persist consumed-token and optimizer-state ledgers for resumable
training. Preserve failed attempts and actual billed cost; do not erase failed
attempts from the study's total expense. A budget or resume-integrity violation
blocks a supported outcome, rather than becoming an excuse to discard an arm.

Report non-padding tokens, supervised tokens by target type, steps, unique
lineages, repeat exposure, wall time, GPU type, GPU-hours and actual cost.
Token-budget matched does **not** mean FLOP-, time- or cost-matched.
No numerical token or financial budget is approved in this draft.

## 5. Stage sequence and evidence custody

| Stage | New training | Evaluation | Meaning |
|---|---:|---|---|
| A development screen | 2 runs | 24 fresh cases per A arm; 48 responses | Adaptive development signal |
| Broader qualification plus B replication | 2 B runs; reuse both frozen A models | 48 fresh locked cases per model, all four models; 192 responses | Paired-seed qualification |
| Independent transfer successor | None for frozen candidates | New independently authored institutions and frozen controls | Transfer evidence only |

The proposed broader budget is 48 cases, so 192 responses across the four
models. This is a deliberately small qualification budget, not a demonstrated
minimum sample size. Additional controls, retries due to
infrastructure, development failures and training costs are not included in those
candidate-response counts.

1. Register the A training/screen artifacts and gates before training or scoring.
2. Train Ordinary A and ActionNet A; freeze both adapters and manifests.
3. Evaluate the 24-case screen under frozen prompts, decoding and resource rules.
4. If supported, freeze the final recipe without changing the A adapters. If
   changing it, label the screen as development and register a new experiment;
   old A models no longer replicate the changed recipe.
   A separate replication run may set `training_seed_label` to `B`; the B seed
   itself is already frozen in `config.json` and cannot be selected from results.
5. Register seed B, exact broader size, coverage, baselines, all gates and analysis
   before any broader seed-A results are visible. Commit the protected instrument
   or its controlled materialization procedure with an identified custodian.
6. Train and freeze Ordinary B and ActionNet B with the registered recipe.
7. Evaluate all four models in one locked broader scoring transaction. Physical
   jobs may run sequentially; outputs and interim scores remain unavailable for
   candidate/prompt selection. Resume only bound missing work under frozen rules.
8. Release all four outcomes and paired comparisons together. Preserve incomplete
   work and failures; never release only the most favorable seed.

Gold labels remain unavailable to inference. Prompts, parser, executor, runtime,
decoding, per-case limits and timeout behavior must be frozen. Predeclare handling
of malformed outputs, truncation and model-caused timeouts; they must not disappear
from denominators. Distinguish these from independently documented infrastructure
failures. No unregistered sampling retries or reference-guided output repairs.

## 6. Shared metrics and outcome rules

The primary endpoint is complete native operational-program correctness on the
shared output interface. Freeze its exact conjunction: coverage, canonical order,
EXECUTE/DEFER, execution-derived state, decision and any shared required certificate.
The native executor/schema determines timing, tie-breaking and legal decisions;
do not silently replace inherited semantics or invent additional decision classes.

Report separately:

- Event coverage, ordering and execution/defer correctness.
- **Model-predicted state accuracy**, if required by the common schema.
- **Executor-computed state accuracy**, derived from the emitted program.
- Decision accuracy and consistency with the program's execution.
- Complete-program correctness and counterfactual pair joint correctness.
- Unsafe proposals, unsupported claims and missed restrictions.
- Useful correct authorizations and unnecessary abstention, on explicit eligible
  subsets; refusal is not a substitute for correct useful work.
- Retention on a preregistered previously-working mechanism stratum.
- ActionNet auxiliary trace quality as a separate diagnostic, not a control penalty.

Freeze raw unsafe and unexamined-output definitions. A malformed proposal cannot
be counted as safe just because it was unparseable. Report eligible denominators
and missingness for every metric. Reference-assisted correctness checks are
offline oracle-assisted evaluation, **not** a deployable operational verifier.
Committed-action safety and episode completion are NOT ESTABLISHED by this static
screen; mark them not measured unless a separately validated runtime measures them.

For each seed s, calculate the paired complete-program difference
Delta_s = accuracy(ActionNet_s) - accuracy(Ordinary_s). Broader support requires
both Delta_A and Delta_B to meet the registered advantage threshold and all
absolute/retention gates independently. Pooled improvement cannot rescue a failed
seed. Shared cases, counterfactual pairs and family clusters must be reflected in
the preregistered uncertainty analysis; do not treat every generated answer as an
independent draw. Two seeds support only the stated limited replication claim.

| Outcome | Rule to instantiate before scoring |
|---|---|
| SUPPORTED | Valid complete experiment; every required absolute, safety, usefulness, retention and within-seed comparative gate passes |
| NOT_SUPPORTED | Valid evidence violates a hard gate or meets the registered clear-loss/regression criterion |
| INCONCLUSIVE | Valid complete evidence meets neither support nor clear-rejection criteria |

Operational status is separate: NOT_RUN, INCOMPLETE or INVALID_EXECUTION is not a
scientific win, loss or valid inconclusive result. The screen's SUPPORTED means
permission to propose broader qualification, not proof of transfer or deployment.
Freeze numerical correctness floors, zero-observed-unsafe gate, advantage margin,
retention tolerance, clear-loss criterion, uncertainty method, confidence level,
eligible subsets and subgroup floors before results. Historical thresholds and
illustrative 90%/10-point targets are not automatically adopted here.

## 7. Independent transfer and system attribution

Transfer needs a separate successor identity, independent instrument authorship
and custody, frozen institutions/controls, overlap audits and new execution
approval. Freeze both ActionNet candidates AND the ordinary controls before
protected access if claiming the ActionNet advantage transfers. Register strong
competitive baselines before their results; their selection is not made here.
Test each candidate separately, without protected retraining, prompt repair,
threshold changes or seed selection. Gold-IR and actual compiled-input tracks
must be separate; report compiler fidelity and institution-specific expert effort.

Closed-loop qualification also needs a separate version and interface contract:

| System | Scope |
|---|---|
| Model only | Proposals and predicted outcomes in simulation, no consequential commits |
| Model + State Engine | Execution of proposals in a sandbox |
| Model + State Engine + Kernel/operational verifier | Governed behavior with a tested authorization boundary |
| Engine-only controller | Fully specified deterministic planner/controller with matched observations and resources |

An executor alone is not a planner baseline. Compare these systems on time-gated
observations, plans, resource limits, rejection recovery, outcome monitoring,
replanning and safe termination. Separate unsafe proposals from committed actions,
unaided completion from human-assisted recovery, and learned contribution from
deterministic protection. No hidden oracle answers may enter the deployed verifier.
Cheap development simulation may proceed separately; it does not count as protected
qualification or reopen the historical closed-loop/capstone protocols.

## 8. Commercial evidence and optional work

A permissioned read-only shadow pilot is a separate customer-value study requiring
a willing partner, data rights, restricted handling, human review, spending/stop
rules and no autonomous consequential commits. Compare the existing workflow;
measure review burden, missed constraints, false alarms, latency and cost. Label
projected recovery-time or savings benefits as projected when actions were not
implemented. No customer relationship, outreach or paid pilot is assumed.

Comparison-001, scaling curves, component ablations and additional model sizes are
optional, question-driven investments. Scaling need not precede transfer. Legacy
mini-IGI is a separate future qualification, not a prerequisite for every narrower
research or customer-value claim and not passed by this contract.

## 9. Required evidence bundle at registration and release

Registration must bind the exact contract, configs, dataset inventory and split
commitments, serializers, tokenizer, starting weights, optimizer/adapter settings,
seed streams, trainer, inference runner, parser, executor, scorer, runtime, prompts,
gate definitions, custody rules and budget approvals by content hash. Record who
approved the study and where the commitment is held. A local hash alone is not an
independent timestamp or an external signature. Do not create registration.json
until commitments are complete; freeze each stage under its explicit identity.

Release preserves all planned models and training manifests, token/exposure and
cost ledgers, bound raw outputs, failure inventory, all subgroup metrics, paired
comparisons, uncertainty estimates, deviations and outcome. Changing a frozen
recipe, gate or protected instrument requires a new version/identity, never an
overwrite or an unreported replacement.

Runner timing multiplied by a registered hourly price is only a live spending
estimate. Final scoring also requires a registration-bound provider billing
receipt naming the Modal account, included A-stage jobs, actual GPU hours, actual
cost and a hash of the retained provider evidence. Estimates are not relabeled
as an invoice.

## 10. Registration blockers and approval boundaries

| Before | Missing commitment / deliverable |
|---|---|
| A registration | Verified final Program-005 audit and documented successor rationale, including any HOLD |
| A registration | Materialize and review the implemented 384-scenario fresh inventory, coverage, provenance and complete-pair exclusion audit |
| A registration | Review the implemented shared native schema and ordinary/ActionNet serializers against materialized token plans |
| A registration | Downloaded base/tokenizer hashes, license review, adapter/optimizer/runtime/seed settings |
| A registration | Numerical training-token budget, tolerance, exposure schedule, tokenization feasibility audit |
| A registration | Exact 24-case coverage/retention design, scorer fixtures, numerical gates and uncertainty rules |
| A execution | Real-L4 rehearsal of the implemented trainer/inference/accounting/resume path, positive time/cost caps and separate explicit execution approval |
| A final scoring | Complete bound outputs for both arms and an attested provider billing receipt within the registered caps |
| Broader registration | Exact 48-case protected coverage, seed B, four-model commitments, analysis/gates and custodian |
| Broader execution | Both B adapters frozen, protected release/resume rules and separate spending approval |
| Transfer / closed loop / pilot | New protocols, controls, interfaces, permissions, qualification gates and budgets |

These blockers are deliberate. This deliverable is the written contract, not a
claim that the implementation, financial choices or statistical design are ready.