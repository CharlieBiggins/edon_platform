# ActionNet comparison 001 — CPU framework, not a launched experiment

Built September 14, 2026. Status:
`CPU_FRAMEWORK_PENDING_PROGRAM005_AND_BASELINE_CONTRACT`.

Question: does the Program005 targeted causal-supervision/rehearsal package
improve a frozen 4B model's institutional computations beyond its base, parent,
ordinary continuation, and a preregistered open-weight alternative?

This is an adaptive **development screen**. It is not a two-seed qualification,
protected transfer, production-verifier test, customer pilot, or mini-IGI result.
No model imports, downloads, package installation, training, API calls, or GPU
launch occur in this framework. Do not run another Program005 preparation or
change its registered source, data, predictions, scores, or thresholds.

## What is executable

1. `preflight`: report framework status, response count, and missing prerequisites.
2. `audit-program005`: verify a complete restored run and original parent adapter;
   replay all three raw prediction files through the unchanged scorer; require
   exact agreement with every score and selection result. Preserve either PASS
   or HOLD in a new audit directory. An incomplete run cannot become a completed
   audit. This is CPU replay of saved outputs, not model generation.
3. `prepare-screen`: repeat that audit, require its screen-success disposition,
   a completed candidate/interface/budget contract and actual interface/baseline
   hash matches; generate 48 new cases; validate targets and exclusion coverage;
   publish a new locally immutable screen registration and label-free inputs.
4. `score`: require all five complete, bound raw prediction files, run the
   inherited scorer, preserve raw unsafe/unexamined claims, report reference-
   assisted verification separately, and write a new comparison report.

Preparation cannot proceed with the provided incomplete contract. It cannot be
unlocked by editing a copied audit report: it replays the actual Program005 run.
A Program005 HOLD requires a new repair proposal/protocol, not a threshold edit
in this package. This framework has **no paid inference runner**. Supplying a
runner hash is a prerequisite, not evidence its implementation is correct.

## Conditions and compute

| Condition | Frozen identity / purpose |
|---|---|
| `base` | Original Qwen/Qwen3-4B-Instruct-2507 revision; no adapter |
| `parent` | Original Program003 trace adapter; retention reference |
| `ordinary` | Completed Program005 ordinary step-24 adapter |
| `targeted` | Completed Program005 repair step-24 adapter; fixed candidate |
| `open_weight_alternative` | User-chosen, licensed snapshot and commit pinned before cases/results |

This adds a parent reference to the proposed model comparison. **48 cases x 5
conditions = 240 responses**, not 48 or 192. This screen reuses completed adapters;
it does not start another training run. The two Program005 continuations share
one trained parent and one continuation seed: there is NO two-seed replication.

Only the ordinary/targeted pair has matched training record exposure. Their token
compute is NOT matched. Models must get the same observation and output task,
no oracle state, no inference-time verification tools, zero retries and greedy
decoding. Tokenizer/chat-template differences must be documented in the frozen
runner. Input/output caps are 4096 tokens each on the reserved L4 hardware class;
token qualification on the real chosen models remains outstanding. Missing or
over-budget cases cannot be silently truncated/dropped. Each response reports
token counts and duration; each condition reports GPU time and cost.

The contract needs positive spending/time caps and a reason why a screen is
worth doing before a larger study. The CPU scorer flags exceeded budgets but
**cannot enforce a remote spending limit**. A future paid runner must enforce
the cap and resume bound prefixes without changing cases or thresholds.

## Cases, gates and limits

Exactly 24 ordinary cases plus 24 targeted cases (two whole counterfactual pairs
per each of six inherited repair rules). All five certificate decisions must be
present: ALLOW, DENY, ABSTAIN, CONTESTED, INVALID. Decision quotas are reported,
not represented as a six-class balance. ESCALATE/REVISE/REASSIGN are not new
certificate classes in this protocol. Inherited timing is EXECUTE iff event
time <= query time, ordered by the complete registered key.

Generation uses the frozen Program005 generator in a separate process with new
family ranges and generation seed. It excludes the bound 003/004 source
fingerprints plus all 005 training/development fingerprints. Case/pair/family
IDs and prompts are also checked against the supplied 005 exposure. Exclusions
do not establish independence from every historical or external exposure. The
instrument is familiar synthetic development, not independently authored transfer.
It does NOT claim four direct cases across 18 mechanisms.

Fixed candidate `targeted` must satisfy the inherited absolute program gates,
95% trace floor, zero raw/derived unsafe and unexamined claims, at least one
joint-correct pair out of two for EACH targeted rule, and at least **two additional
exact cases** versus EACH of the four reference conditions. It must not lose
ordinary exactness, decision/state/order accuracy or useful ALLOW behavior versus
ordinary and parent. Useful-ALLOW errors/abstentions use the oracle-ALLOW subset.
An observed ordinary-retention tie is not proof of population noninferiority.

These are deliberately explicit proposed engineering screen gates, not an
established minimum sample size or a significance claim. They are frozen with
the eventual registration before prediction. Never choose the least-bad model
after all candidates fail. No subset success or early stopping for significance.

Outputs: `SCREEN_HOLD`, `SCREEN_HOLD_BUDGET_DEVIATION`, or
`SCREEN_SUPPORTS_NEW_QUALIFICATION_DESIGN`. All leave selected_arm null and
confirmation/transfer/authority false. A pass supports designing a separate
fresh 96+ case/two-continuation-seed qualification, not automatically launching
one. Old Transfer008 and Capstone001 are not reopened or edited.

## Critical verifier distinction

The inherited scorer's `accepted_by_verifier` consults oracle/reference state
and certificates. It is **ORACLE-ASSISTED EVALUATION**, NOT demonstrated deployable
verification. The same output is measured for raw correctness and reference
acceptance. No silent correction, resampling, or sanitized replacement is allowed.
Rejecting an unsafe claim must not erase the raw unsafe count. A new deployable
executor/Kernel integration needs its own implementation, trust-boundary tests,
and reference-free runtime evaluation; see ARCHITECTURE.md.

## CPU commands (from workspace root)

```sh
python -B -m unittest discover -s edon/experiments/CEREBRUM-ACTIONNET-COMPARISON-001/tests -v
python -B edon/experiments/CEREBRUM-ACTIONNET-COMPARISON-001/run.py preflight
```

The integration test reconstructs frozen data and scores oracle fixtures in a
temporary workspace, then removes them. It is not an experiment or model result.

After Program005 finishes, use actual relative restored paths (examples below
are placeholders, not commands claiming those directories currently exist):

```sh
python -B edon/experiments/CEREBRUM-ACTIONNET-COMPARISON-001/run.py audit-program005 --workspace restored005 --parent-search restored-parent --output-dir audit005-final
python -B edon/experiments/CEREBRUM-ACTIONNET-COMPARISON-001/run.py prepare-screen --workspace restored005 --parent-search restored-parent --contract comparison-contract.json --interface-dir comparison-interface --alternative-dir alternative-snapshot --output-dir comparison001-screen
python -B edon/experiments/CEREBRUM-ACTIONNET-COMPARISON-001/run.py score --workspace restored005 --screen-dir comparison001-screen --predictions-dir comparison001-predictions --output-dir comparison001-scores
```

Copy `contract.template.json` to a separate file and complete it only after
baseline/interface selection and budget approval. Do not modify a published
screen. Export only `screen-inputs.jsonl` to the inference process; the
`screen-reference.jsonl` file contains scoring targets and must not be mounted
where the model runner can inspect it. The CPU framework does not enforce
remote filesystem isolation. See PREDICTION_CONTRACT.md before writing a runner.

Output directories must be new and outside source/input trees. Failed output
directories are preserved for audit; never delete them to bypass a mismatch.
Source and content hashes are local commitments, not external signatures or
proof that remote source writes were atomically downloaded.

## Remaining work before any paid comparison

- Complete, verify and replay Program005 (actual results not present here).
- Choose the alternative and review its license; no model selected on your behalf.
- Implement/audit a common inference runner, prompt pack and runtime lock.
- Qualify tokenizer budgets and runtime without changing the output task.
- Set spending caps, approve the extra screen, and freeze the contract.
- Register the generated screen; then separately authorize any paid execution.