# Cerebrum compatibility entry

Cerebrum is now the complete non-authoritative institutional-intelligence
system. C1 is the learned-model layer inside it.

Historically, EDON experiment documents used “Cerebrum” for the learned
component. Those frozen experiment IDs, artifacts, metrics, and claims retain
their original terminology. This architecture migration does not promote a
model-only result into a full-system result.

See `cerebrum-system.md`, `c1-model-layer.md`, and
`cerebrum-terminology-migration.md` for the canonical definitions.

## C1 responsibilities

- interpret institutional observations and candidate state;
- reason about policy, authority, causal comparisons, and uncertainty;
- predict semantic states and bounded downstream effects;
- support planning and produce typed non-binding proposals;
- compare counterfactual mechanisms; and
- abstain when evidence is insufficient.

## Reserved latent-coordination capability

`CEREBRUM-LATENT-COORD-001` defines—but does not implement or validate—a
state-mediated coordination reasoning path. Its input representation includes
agent communications and actions, artifacts, database/state mutations,
resources, queues, schedules, code/configuration changes, causal dependencies,
and artifact lineage.

The registered reasoning sequence is:

```text
detect -> attribute -> reconstruct -> predict -> govern
```

The output is a non-binding coordination hypothesis containing participants,
an evidence-grounded causal path, an objective hypothesis, predicted effects,
competing explanations, uncertainty, risk, and a recommendation for
deterministic policy evaluation. No learned detector or performance result
currently exists. See `latent-institutional-coordination.md`.

## Institutional resilience research direction

The broader resilience direction asks whether the Cerebrum System can detect
and reconstruct poisoned state, cross-system cascades, resource exhaustion,
authority confusion, and compromised components; forecast affected objectives;
and emit bounded containment, degraded-operation, or recovery proposals.

Every output remains non-binding. This is a threat model and evidence roadmap,
not a validated attack detector, critical-infrastructure defense, or
national-security capability. See `institutional-resilience.md`.

## C1 prohibited responsibilities

- binding authorization;
- direct policy mutation;
- automatic promotion of learned exceptions;
- training on protected evaluation labels;
- hiding conflicts or uncertainty;
- converting a coordination hypothesis directly into intervention authority;
- converting a resilience or compromise hypothesis directly into containment
  authority;
- committing observed, reported, inferred, authorized, or committed state; and
- performing institution-specific weight updates inside production operation.

Learned changes require fresh identities, frozen data boundaries, registered
seeds, and independent evaluation.

## Implemented orchestrator

The campaign orchestrator prepares separated public/protected directories,
records qualification and data hashes, plans or launches tokenized seed commands
without a shell, freezes predictions by seed, and summarizes multi-seed gates.

The end-to-end demo uses an oracle-derived reference diagnostic to exercise this
plumbing. It is marked `learning_claim=false` and must not be reported as model
training evidence.

## Local C1 operations provider

`CEREBRUM-BUILD-001` adds an opt-in local Qwen provider for the operations
shadow loop. The provider supports a Qwen base model with an optional PEFT/LoRA
adapter, deterministic decoding, strict single-object JSON parsing, fail-closed
abstention for malformed generation, and hard rejection of authority-bearing
output. The optional GPU dependencies are loaded lazily, so the
deterministic EDON runtime and repository validation remain dependency-free.

The provider is disabled by default. Enabling it requires an explicit model
lineage, and every output still passes through the typed operations adapter and
immutable shadow supervisor. No learned output can issue a Kernel token or
commit world state.

This is provider integration, not a trained Build-001 model result or an
evaluation of the complete Cerebrum System.