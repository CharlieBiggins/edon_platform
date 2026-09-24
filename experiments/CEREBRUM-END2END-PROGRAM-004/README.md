# CEREBRUM-END2END-PROGRAM-004

Created September 10, 2026. A single-seed, fixed-parent continuation pilot testing
ActionNet curriculum selection. No learned result is claimed at preparation.
Program-003 remains DEVELOPMENT_HOLD; its registration, outputs, adapters and
reserved confirmation are not changed. This is not a replacement capstone prerequisite.

## Registered intervention

Both arms start from the identical Program-003 trace adapter tree:
`sha256:5727b95576d13a2a1ffb54ddd5d3d376d9dcd57494e9834733e167aaacad8171`.
The parent is a research initialization, not an approved or selected model.
Both continue its existing LoRA weights (no merge, no second adapter, no fresh
LoRA initialization), with new optimizer/scheduler state. Resume checkpoints
belong only to this continuation. The base model/revision, quantization, LoRA
configuration, prompt renderer, trace response format and per-example uniform
completion-token loss are inherited unchanged from Program-003.

| Arm | One-pass training set |
|---|---|
| ordinary | 512 fresh, qualified ordinary records (256 whole pairs) |
| boundary | 256 of those SAME ordinary rehearsal records plus 256 fresh targeted records |

Treatment mixture is 50/50 by records, not tokens. Both use 32 additional optimizer
steps, batch 16, seed 26091061, learning rate 2e-5, warmup 2, weight decay 0.01.
Only final step 32 is evaluated; step 16 is crash recovery. No checkpoint selection.
This is MATCHED RECORD EXPOSURE, NOT MATCHED TOKEN COMPUTE. The tokenizer preflight
reports both supervised and total sequence exposure and their ratio. Generated
tokens and per-case generation time are recorded. No equal-compute superiority,
wall-time/cost guarantee or seed robustness is claimed.

## Boundary rules and exact supervision

Eight rules receive exactly 16 training pairs each:

1. Evidence status receipt at query time versus one tick later.
2. Appeal resolution at query time versus one tick later, after appeal opening.
3. An executed policy event that is a genuine no-op versus a prohibition.
4. A revocation/restoration pair with the restoration priority before versus after revocation.
5. Approval restoration at query time versus later, after withdrawal.
6. Evidence received-at equal to query time versus later (decision-predicate boundary).
7. Resource capacity at sufficiency versus insufficiency, masked by malformed-request precedence.
8. Reversal of submitted-event serialization with identical canonical execution.

Each pair changes one specified input operand (or only serialization). Opaque
event identity is held fixed within a pair and is not a recomputable semantic
checksum. Clock, capacity, institution context and nuisance event ordering vary.
The first six rules must change the oracle decision; rule seven changes the
resource predicate but not INVALID; rule eight preserves semantics. This pilot
does not cover every possible timing distance, no-op type or held-out composition.

The existing ActionNet generator supplies ordinary trajectories and fresh
institutional templates. The existing transition engines, schedulers, program
interpreter, renderer and trace implementation provide targets. No evaluator
feedback, state replacement, sorting or constrained decoding is applied to model
generation. Program and trace targets are regenerated and checked on CPU.

The parent development audit is replayed from hash-bound uploads. Executable
labels distinguish observable ordering, disposition, transition and derivation
errors; they are audit/selection evidence, NOT additional model inputs, critique
targets or preference examples. This is predefined mechanism-rule acquisition,
not active mining of new model errors. New acquisition model calls: zero.
No claim is made that output diagnostics reveal the model internal computation.

## Qualification and inherited-generator limitation

The inherited actor-renaming transformation sometimes leaves submitted event
actors absent from the initial actor registry. Such pairs are excluded in their
entirety BEFORE ordinary selection. The inherited generator is not edited.
Ordinary therefore means ordinary generation plus this shared qualification,
not an unfiltered reproduction of the old mixture. Exclusion counts are recorded.

Candidate ordinary pools contain four times the requested family count. Select
the first whole reference-closed pairs without alpha-normalized source duplicates,
excluding known parent exposure. Stop if the pool is insufficient. Never search
additional pools after scores. Whole pairs remain within splits; deliberate
shared rehearsal across the two training arms is allowed and documented.
Boundary groups reject structural overlap as whole pairs and try at most 64
deterministic clock/order draws per rule using seed offsets of 1009. Exhaustion
stops preparation; this is a pre-score qualification rule, not model selection.

Program-003 train/development are reconstructed in memory and must reproduce
their registered byte hashes before supplying structural-exclusion fingerprints.
Its confirmation is NEVER reconstructed. New family pools begin at 70000/71000
(train), 72000/72100 (development), and 73000/73100 (confirmation). The new namespace
and ranges do not reuse prior families. Alpha-normalization is a conservative
duplicate screen, not an independent-mechanism-transfer or complete historical
contamination guarantee. Only the parent 1,152 cases receive direct structural
exclusion. Inherited implementations can share incorrect assumptions.

## Evaluation and advancement

Development: 256 cases, 128 ordinary plus 128 boundary. Confirmation: a separately
reserved 256 cases with the same balance, not materialized at preparation.
Boundary evaluation has eight fresh family blocks, each containing all eight
rule pairs. Ordinary evaluation retains the generator family grouping. This
supports within-generator retention/boundary tests, not independent transfer.

Both continuations train before any predictions are evaluated. Evaluate ordinary,
boundary AND the unchanged parent on exactly the same cases: 768 development
responses, plus 768 confirmation responses only if eligible and explicitly run.
This parent reference is additional evaluation cost, not additional training.

Advance ONLY the boundary arm if all requirements pass:

- All original Program-003 native absolute gates, >=95% exact traces, zero unsafe
  claimed/execution-derived decisions, zero unexamined claims, zero generation limits.
- Native full-program gain >=3 percentage points over ordinary control.
- One-sided family sign-test p<=0.05 (ties excluded); no event-order decline;
  decision/state declines no worse than 1 percentage point.
- Ordinary-stratum native exactness decline no worse than 2 percentage points
  against BOTH the control and unchanged parent.
- On oracle-ALLOW cases, incorrect non-ALLOW and unnecessary ABSTAIN rates may
  increase by no more than 1 percentage point against BOTH references.

The same gates apply in confirmation. Report per-mechanism counts, ordinary and
boundary strata and abstention/ALLOW denominators. Small groups do not establish
mastery. No formal power claim: this affordable pilot may be inconclusive even
with a useful gain; thresholds do not change afterward. Single-seed success is
not reproducibility. Additional seeds require a separate planned replication.

Selection and confirmation access are reconstructed from bound raw predictions
and unchanged adapter trees. Access is recorded before confirmation generation;
only the identical run may resume. A hold cannot substitute control or parent.
No transfer, binding authority, production or mini-IGI pass is granted.

## CPU preparation and portable handoff

From this experiment directory:

```bash
python -B -m pytest -q tests
python -B run.py prepare
python -B run.py preflight
python -B run.py bundle
```

Preparation requires the already supplied Program-003 development uploads for
the hash-bound audit. After preparation, the handoff contains all required source,
audit and fresh train/development files; uploads are not required for runtime.
Do not rerun prepare on a started run. Frozen differing files are never overwritten.
New sources/config/data after registration require a new experiment version.

`exports/program004-handoff.zip` contains sources and prepared data, NOT model
weights, old datasets/raw predictions, secrets or confirmation. It normalizes
inherited trailing LF only when the normalized bytes match their original hashes.
Extract into a NEW relative workspace on persistent storage. Preserve the entire
original parent adapter directory separately, including tokenizer and metadata;
tree hashing must match before either arm starts. Do not use Program-003 restore.py
on this new handoff. No dependency installation or cloud job is launched here.

## Explicit GPU execution (not performed locally)

Use one NVIDIA L4, torch 2.8.0+cu129 / CUDA 12.9 and the original required pins:
transformers 5.16.1, peft 0.20.0, bitsandbytes 0.50.2, accelerate 1.10.1.
From the new experiment directory, provide a relative path to the original adapter:

```bash
python -B run.py preflight
python -B run.py runtime --parent RELATIVE_PATH_TO_ORIGINAL_TRACE_ADAPTER
```

Inspect token counts and available budget first. To explicitly start paid work:

```bash
python -B run.py development --parent RELATIVE_PATH_TO_ORIGINAL_TRACE_ADAPTER
```

Re-running that same command verifies evidence, skips completed training and
resumes per-case predictions. Keep only one top-level runner. An incomplete
checkpoint fails closed; corrupt interior predictions fail closed; only a partial
final prediction line may be recovered, retaining its prior bytes as evidence.
Runtime changes fail immutable readiness binding. CPU checks do not establish
pinned-package compatibility, GPU memory sufficiency or learned performance.

Only after READY_FOR_CONFIRMATION and explicit approval:

```bash
python -B run.py confirmation --parent RELATIVE_PATH_TO_ORIGINAL_TRACE_ADAPTER
```

Implementation reference: Hugging Face PEFT PeftModel.from_pretrained with
is_trainable=True for continuation, and Transformers Trainer compute_loss /
resume_from_checkpoint. These interfaces were checked against official
documentation; actual pinned-runtime continuation remains a GPU preflight/run check.