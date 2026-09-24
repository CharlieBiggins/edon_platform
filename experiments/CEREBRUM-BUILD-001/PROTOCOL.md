# CEREBRUM-BUILD-001 engineering protocol

## Objective

Build an exploratory institutional-intelligence system that combines a local
Qwen reasoning model with ActionNet context, persistent world and episodic
memory, typed operations, tools, monitoring, replanning, and deterministic
Kernel enforcement.

This is an engineering protocol, not a preregistered scientific result.
Architectures, curricula, prompts, hyperparameters, and error repairs may change
under new versioned build manifests.

## Separation from confirmatory research

- RB1 artifacts and dispositions are immutable inputs to their own protocol.
- Transfer-008 remains blocked and unmaterialized under its existing gates.
- Build-001 may not train on protected Transfer-008 material.
- Build outcomes may motivate a future research identity but cannot be inserted
  retroactively into RB1 or Transfer-008.

## Runtime boundary

The learned model may emit only `ABSTAIN`, `CREATE_GOAL`, `CREATE_PLAN`,
`DISPATCH_STEP`, `REPLAN`, or `CANCEL_STEP`. Every accepted proposal is:

1. parsed as one JSON object;
2. checked for required typed fields;
3. stripped of any authority claim by rejection rather than repair;
4. bound to its context and explicit model lineage by SHA-256;
5. written to immutable shadow custody;
6. recorded with `binding_authority=false` and `executed=false`.

No model output can mint a Kernel token or commit world state.

## Training boundary

Exploratory weight updates require a versioned training-release manifest. The
release must list source datasets, hashes, permissions, overlap checks, task
counts, and exclusions. Protected evaluation labels, real-institution raw data,
and ActionNet records that remain `training_eligible=false` are prohibited.

The initial intended model is `Qwen/Qwen3-4B-Instruct-2507` with QLoRA. Larger
or smaller models require a new build version, not a research claim.

## Benchmark boundary

Controllers receive the same observations, tools, time horizon, retrieval
budget, and action vocabulary. The registered controller classes are:

- deterministic reference;
- unmodified base model;
- ordinary tool-using model agent;
- operations-research solver where applicable;
- Cerebrum build candidate;
- Cerebrum plus validated operations-research solver.

Development cases may be inspected and iterated upon. A separate protected
benchmark identity is required before any generalization claim.

## Engineering graduation gate

An internal shadow candidate may advance when it has:

- zero authority-field acceptance and zero unsafe/unauthorized recommendations;
- valid typed proposals on every scored case;
- no generation-limit failures on the selected internal benchmark;
- reproducible artifact and prediction hashes;
- measurable improvement over the unmodified base on the declared primary
  institutional tasks;
- no regression below the deterministic safety floor;
- completed multi-cycle observe--plan--allocate--monitor--replan evaluation;
- an explicit model card and rollback artifact.

Passing this gate would authorize a larger internal shadow evaluation only. It
would not establish IGI, independent transfer, or production readiness.