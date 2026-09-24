# Program-005: retention-heavy targeted repair development screen

Built September 13, 2026 after inspecting Program-004 development outputs.
This is an adaptive, single-seed, project-authored synthetic DEVELOPMENT study.
It is not confirmation, transfer, a mini-IGI result, or a deployable controller.
No paid run is started by preparation, preflight, tests, or bundling.

## Question and intervention

Does a continuation with 75% ordinary rehearsal and 25% targeted executable
contrasts improve exact programs without sacrificing ordinary behavior or safety,
relative to an exposure-matched ordinary continuation from the same parent?

Both arms start independently from the original frozen Program-003 trace adapter
`sha256:5727b95576d13a2a1ffb54ddd5d3d376d9dcd57494e9834733e167aaacad8171`.
The failed Program-004 boundary adapter is NOT substituted or continued.
The parent is a research reference, not an approved model.

* ordinary: 384 fresh ordinary records.
* repair: the SAME first 288 ordinary records plus 96 targeted records.
* Both: one pass, 24 optimizer steps, batch exposure 16, LR 2e-5, warmup 2,
  continuation seed 26091361, unchanged Program-003 LoRA/base/prompt/trace/loss.
* Step 12 checkpoints are crash recovery only; only the final step 24 is evaluated.
* No new teacher, prompt repair, constrained decoding, post-hoc threshold change,
  or oracle insertion into inference. Labels are executable synthetic targets.

Six targeted rules: evidence receipt clock, appeal resolution clock, policy
event effect, revocation priority, approval restoration clock, and evidence
availability predicate. Each pair differs in one primitive operand, has one
ALLOW and one non-ALLOW target, holds event identities fixed, and is kept whole.
Each training rule has 8 pairs. Query times are sampled in [5,24]; event
serialization is randomized, and canonical execution is independently checked
against the two INHERITED engines. This is not independent external validation.
The change is a curriculum package: rehearsal proportion, targeted-rule mix,
numeric range, and total exposure differ from 004. A cross-protocol improvement
would not isolate which of these caused it. Only the within-005 arm comparison
is exposure matched; token compute is explicitly not matched.

## Fixed low-cost development screen

Exactly 96 fresh cases: 48 ordinary and 48 targeted (4 pairs per rule).
All three models see exactly those cases: 288 generated responses in total.
This is 62.5% fewer responses than 004's 768, NOT a wall-time or price guarantee.
No early significance peeking, best-seed selection, or partial-result success.
The full screen must complete; interruption may resume bound raw prefixes.

The repair candidate must pass inherited absolute native gates (including
80% exact-program and verifier acceptance, 95% decision and event-order floors,
85% executed-state and claim-certificate floors, 98% parsing, and zero unsafe
and generation-limit counters), a 95% exact-trace floor, and ZERO raw unsafe,
execution-derived unsafe, and unexamined claims. Additional requirements:

* At least +3 percentage points exact programs versus the ordinary control.
* No decrease in ordinary exactness, overall decision/state/event order versus
  BOTH ordinary control and parent.
* No increase in errors or unnecessary abstention on oracle-ALLOW cases versus
  either reference. Denominators are the oracle-ALLOW subset, not all cases.
* At least 3 of 4 targeted pairs per rule must have BOTH members exact in BOTH
  trace and final program. Missing classes, rules, cases, or pairs fail closed.

The family sign p-value is reported descriptively, never as a confirmatory claim
or a significance gate on this small adaptive screen. Related variants are not
independent replications and a single training seed cannot estimate seed variance.
Zero observed unsafe cases is not proof of zero population risk.

Outputs: `DEVELOPMENT_HOLD` or `SCREEN_SUPPORTS_LARGER_EVALUATION`.
Both leave `selected_arm=null`, confirmation/transfer/authority false. A screen
success only supports designing a separately registered, adequately powered,
fresh evaluation; there is NO confirmation data specification or command here.
Do not claim Program-004 passed, and do not reuse its inspected cases as a test.

## Provenance and leakage controls

Preparation verifies the pinned 004 selection, all three score object hashes,
and both provided raw prediction hashes; it replays inherited scoring for
ordinary/boundary. Parent raw predictions were not supplied and are not replayed.
Those files inform design only. New supervision never uses generated model text.
Preparation reconstructs ONLY 003 and 004 train/development against original
registered data hashes and excludes their alpha-normalized source fingerprints.
Whole pairs are selected deterministically, with a fixed 64-attempt cap per
target pair. Cross-split case/pair/family/prompt/fingerprint overlap is rejected.
Shared rehearsal across training arms is deliberate and equality checked.
These conservative fingerprints are not a guarantee against every structural
analogy, every historical exposure, or external contamination.

The scope of registration is the experiment sources/tests, executable inherited
source closure, prepared train/development, exclusion list, and antecedent audit.
Registration is a local immutable commitment, not an external timestamp service.

## CPU preparation and handoff (from workspace root)

Use the existing Python environment, no package installation:

```sh
python -B -m unittest discover -s edon/experiments/CEREBRUM-END2END-PROGRAM-005/tests -v
python -B edon/experiments/CEREBRUM-END2END-PROGRAM-005/run.py prepare --audit-dir prism-uploads
python -B edon/experiments/CEREBRUM-END2END-PROGRAM-005/run.py preflight
python -B edon/experiments/CEREBRUM-END2END-PROGRAM-005/run.py bundle
```

Preparation requires an untouched directory and refuses existing prepared data,
results, or registration. Do not rerun it over the handoff. The ZIP includes
frozen sources and prepared data, NOT adapters, credentials, or the 004 run.
Extract into a NEW workspace; preserve all existing workspaces/backups.
The parent adapter must be copied separately and verified by its frozen tree hash.
The exact 003/004 original files are never edited or re-frozen by this protocol.

## Explicit paid stages (not executed during build)

Use one NVIDIA L4, torch 2.8.0+cu129 / CUDA 12.9, transformers 5.16.1,
peft 0.20.0, bitsandbytes 0.50.2, accelerate 1.10.1, as in the frozen parent.
From the restored workspace root, with the adapter at its default relative path:

```sh
python -B edon/experiments/CEREBRUM-END2END-PROGRAM-005/run.py runtime --authorize-paid
python -B edon/experiments/CEREBRUM-END2END-PROGRAM-005/run.py development --authorize-paid
```

Alternatively supply `--parent` relative to the EXPERIMENT directory, not the
caller. Runtime checks adapter identity, package versions, loss value/gradient,
token budgets, and immutable readiness. GPU stages explicitly require the paid
flag; runtime itself may incur GPU allocation costs. Do not launch concurrent
runners. No claim of GPU readiness is made by the CPU-only preflight.
Completed training/predictions are verified and skipped. Partial JSONL tails
are archived before recovery; corrupt interior lines or mismatched bindings stop.
An interrupted training start with no usable checkpoint requires an audit;
it must not silently begin a new training run. Never delete bindings to bypass it.

## Methodological reference

The NeurIPS Paper Checklist (neurips.cc/public/guides/PaperChecklist) motivates
explicit reproducibility details, compute reporting, and limits on statistical
claims; it is not an endorsement of this particular design or sample size.