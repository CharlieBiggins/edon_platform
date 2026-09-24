# CEREBRUM-END2END-PROGRAM-003

## Purpose and claim boundary

Built September 8, 2026. This is a new, single-seed, matched-case-exposure
experiment, not a continuation or repair of frozen Program-001/002 scores.
Hypothesis: supervising explicit temporal execution and decision derivation
improves native-program correctness relative to ordinary completion supervision.
This is a testable hypothesis, not a promised fix or a compute-efficiency claim.

The preceding CPU architectural ablation is recorded separately in
`audits/claim-replacement.json`. It replaces only claims with interpreter-derived
values on copies of existing Program-002 outputs. It neither changes event steps
nor demonstrates learned improvement. Confirmation is not used for this audit.

## Matched two-arm design

Both arms start fresh from the same frozen Qwen3-4B-Instruct-2507 revision, seed,
LoRA settings, learning rate, 1,024 fresh underlying training cases, and two
complete passes (128 optimizer steps, effective batch 16). No inherited adapter.

| Arm | Training target and generated response |
|---|---|
| `uniform` | Original native temporal program, including state/certificate claims |
| `trace` | Explicit execution trace and decision derivation, then the same native program |

Both use uniform completion-token cross entropy, normalized within each example.
Prompt and padding tokens are masked. There is no structural token multiplier.
Chunked/checkpointed cross entropy uses the same objective in both arms; runtime
preflight checks its value and gradient against an unchunked reference.

The source docket facts and original plain-text renderer are unchanged across
arms. A static response-format instruction differs because the trace arm must
emit the additional trace. No chat-template change, constrained decoder, external
tool call during generation, sorting, claim replacement, or output correction.
The intervention is the trace-supervised response protocol, not an isolated
claim that target supervision alone caused a change with identical prompts.

## Trace contract

The response begins with `ACTIONNET_EXECUTION_TRACE_V1`. For every source event,
in canonical `(time, priority, sequence, event_id)` order, one `TRACE` JSON record
contains the event ID, complete ordering key, query time, EXECUTE/DEFER, and
changes as sorted `[dot_path, before, after]` leaf records. Arrays are whole
leaves. EXECUTE means event time <= query time. DEFER records have no changes.
No-op executed events also have empty changes; they must not be omitted.

`DERIVE` contains nine ordered blocked-condition booleans, the first failure
(or null), decision, and semantic state. The precedence is malformed request,
contest, authority, routing/jurisdiction, policy, false/expired evidence,
unavailable evidence, approval, and resources. First-failure decisions distinguish
DENY from ABSTAIN, CONTESTED, and INVALID. Every trace target is checked against
both schedulers, both transition engines at every event, and both evaluators.

After `END_ACTIONNET_EXECUTION_TRACE`, the model emits the complete original
native program and claims. At inference it receives only the prompt string and
the static arm instruction. Oracle traces, states, and certificates are used
only for supervised training, length qualification, and post-generation scoring.

The evaluator extracts the final program at the registered boundary without
repair. Malformed trace envelopes fail closed. Trace JSON rejects duplicate keys
and non-finite numbers. Trace exactness compares all records and derivation with
the executable target, separately from native-program correctness. A correct
final program cannot make an incorrect trace count as correct. Independently
parsed native-suffix unsafe claims remain visible even if the trace is malformed.
An unparseable claim is reported as unexamined, not semantically safe.

## Exposure, compute, and cost

This pilot is MATCHED CASE EXPOSURE, NOT MATCHED TOKEN COMPUTE. Longer trace targets
add supervised tokens and inference work. A positive result cannot distinguish
the trace protocol from the contribution of its additional compute, and does
not establish that traces outperform an equal-compute control. Such a control
and multiple training seeds would be separate follow-up experiments.

Both arms have the same 4,096-token generation ceiling, 4,096-token input ceiling,
and 8,192-token training sequence ceiling. These differ from Program-002; no
cross-protocol causal comparison is claimed. Zero truncation is enforced.
The actual tokenizer must verify BOTH arms before either starts training.
If budgets or memory are inadequate, stop and version the protocol before a new
run; do not truncate, shorten targets, or extend budgets after inspecting scores.

`results/runtime-readiness.json` reports exact per-arm prompt-plus-target and
completion token counts, planned two-pass token exposure, and their ratio.
Training manifests record runtime metrics and whether resumption occurred;
resumed Trainer runtime covers that invocation, not necessarily the whole run.
Predictions record generated-token counts for inference-cost accounting.
No wall-time estimate is implied by CPU qualification.

Only final step 128 is evaluated. Step 64 is for crash recovery, not model
selection. Total planned work: 256 optimizer steps and 256 development responses.
Eligible confirmation adds 512 responses, only on explicit access. One seed is
a pilot: family-level significance is not evidence of seed robustness.

## Freshness and gates fixed before GPU execution

Training families: 30000-30127. Development: 30200-30215 (128 cases).
Confirmation: 30300-30331 (256 cases), reserved and unmaterialized at preparation.
The new namespace, seeds, and family IDs do not reuse Program-001/002 or DEV-020
cases. Each family has four paired cases (eight records). The generator and
mechanisms are inherited: this is not independently authored or unseen-mechanism
transfer. Audited failed development examples are not copied into training.

The trace arm must satisfy the original Program-001 absolute native-program
floors and zero unsafe-claim/execution-derived-unsafe/generation-limit ceilings.
An additional gate requires >=95% fully exact traces. Native exactness and joint
trace-plus-program exactness are reported separately, and trace exactness is
not attributed to the uniform arm.

The comparison requires native full-program improvement >=3 percentage points,
one-sided family sign-test p<=0.05, no event-order decline, decision and executed
state declines no worse than 1 percentage point, and no unsafe-counter increase.
The same gates apply in development and confirmation. Ties give no positive
evidence; a high-performing control can produce a hold. No best-of-checkpoints
selection, threshold adjustment, or automatic fallback selection of the control.

Confirmation requires a qualifying selection reconstructed from bound raw
development predictions and unchanged adapters. Access is recorded before
generation, then only that identical evaluation can resume. A hold does not
materialize confirmation. No `binding_authority` or `transfer_authorized` grant
is made even on a pass. Closed-loop operation and institutional transfer remain
separate future evaluations.

## Commands and freeze

From this directory:

```bash
python -m pytest -q tests
python run.py prepare
python run.py preflight
python bundle.py
```

Preparation creates train/development data, CPU qualification, and registration.
The registration binds config, protocol document, implementation, tests, inherited
source code and prepared data. Existing differing files are never overwritten.
Changing frozen sources requires a new version/directory, not deleting the freeze.
Do not include Program-002 outputs in a GPU training handoff.

`exports/program003-handoff.zip` includes only registered sources and this new
train/development set, not any predecessor datasets or confirmation data. Its
companion JSON records bundle and registration hashes. If a Prism project export
omits JSONL data or strips a source trailing newline, use `restore.py` with the
trusted registration hash. It only restores a trailing LF when the resulting
bytes match that hash; it does not accept changed code. It regenerates only the
registered train/development records and verifies the original registration.

Example, from the notebook project directory after uploading the ZIP and helper:

```bash
python restore.py program003-handoff.zip program003-workspace --registration-sha256 sha256:HASH_FROM_HANDOFF_JSON
```

Choose a new relative workspace on the attached persistent storage. Do not call
`modal.Volume.from_name(...).commit()` from the notebook setup. This package does
not manage mounts, install dependencies, or start cloud jobs.

In Modal, using the exact package versions in config and one CUDA GPU:

```python
from pathlib import Path
import subprocess, sys
experiment = Path("program003-workspace/edon/experiments/CEREBRUM-END2END-PROGRAM-003")
subprocess.run([sys.executable, "-u", "run.py", "preflight"], cwd=experiment, check=True)
subprocess.run([sys.executable, "-u", "run.py", "runtime"], cwd=experiment, check=True)
```

Inspect the token/runtime report before starting the longer trace experiment:

```python
subprocess.run([sys.executable, "-u", "run.py", "development"], cwd=experiment, check=True)
```

Always use `run.py`; its lock prevents simultaneous top-level runners. Both arms
train before either development prediction is examined. Checkpoint resumption
and per-case prediction resumption require matching registration and evidence.
Only if `results/selection.json` is `READY_FOR_CONFIRMATION` may the user explicitly
run `python run.py confirmation`. A development pass is not a confirmed result.

## Verification limits and references

Local CPU tests do not import torch or download model weights. They test the
generator, trace contract, scoring, gates, masks using a fake tokenizer, and
immutable evidence. Actual pinned-package compatibility, tokenizer lengths,
tensor loss gradients, and GPU memory remain runtime checks in Modal.
Implementation references checked: Hugging Face Trainer compute_loss and
model_accepts_loss_kwargs documentation; PyTorch checkpoint(use_reentrant=False)
and cross_entropy documentation. The inherited generator/evaluator assumptions
are not independently validated by agreement among their implementations.