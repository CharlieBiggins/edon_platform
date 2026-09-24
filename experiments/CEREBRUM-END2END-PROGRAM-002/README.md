# CEREBRUM-END2END-PROGRAM-002

## Purpose and status

Built September 8, 2026 as a separately registered follow-up to the Program-001
development hold. No inherited adapter, overwritten result, or retroactive
threshold change. CPU qualification is distinct from a successful GPU run.

Hypothesis: structural-token loss weighting improves native program correctness
over an equally trained uniform-loss control. This is a new experiment, not an
extension of Program-001 and not a guaranteed repair.

## Matched two-arm design

Both arms start fresh from the same frozen Qwen3-4B-Instruct-2507 revision, use
the same seed, identical 1,024 fresh training records and the same 128 optimizer
steps (two passes, effective batch 16). The same original plain-text augmented
docket prompt, output grammar, generation budget and independent scorers are
used in both arms. There is no chat-template change or output correction.

The sole intended training difference is loss allocation:

| Target tokens | Uniform | Structural |
|---|---:|---:|
| All STEP lines, including event identifiers/dispositions | 1 | 2 |
| Program header, claim prefixes, end marker and EOS | 1 | 2 |
| State/certificate JSON bodies | 1 | 1 |
| Input prompt and padding | 0 | 0 |

Fast-tokenizer character offsets map these regions to tokens; any overlapping
token receives the higher weight. Loss is normalized by the sum of active
weights within each example, then averaged over examples. Thus the intervention
changes which errors receive emphasis without simply doubling the learning rate.
The ordinary control remains uniformly weighted over completion tokens.

Only the final step-128 adapter from each arm is evaluated. Step-64 checkpoints
are for crash recovery, not candidate selection. Total planned cost is 256
optimizer steps and 256 development generations across the two arms. If eligible,
confirmation adds 512 generations. No GPU work is launched by `prepare` or `preflight`.

No untrained baseline is rerun: the equally trained control tests the proposed
repair more directly than another comparison against Program-001's non-parsing
base. This does not resolve the separate baseline prompt/termination question.

## Data and inference boundaries

The existing synthetic generator is reused under the new protocol namespace,
with family IDs 20000–20127 for training and 20200–20215 for development.
IDs 20300–20331 are reserved for 256 confirmation records and are not generated
by data preparation. All are outside Program-001 and DEV-020 family ranges,
including their reserved families. Each family contributes four paired cases
(eight records). The two new arms share the exact same files.

Both parsers and interpreters must accept every oracle target. Split case IDs,
pair IDs and family IDs must be disjoint, with all decision classes represented.
Fresh synthetic families do not establish new-mechanism, real-domain or
independently authored transfer. The audited 13 examples are not copied into
the new training set. Generated datasets retain targets for scoring; generation
receives only the prompt string.

## Gates fixed before GPU execution

The structural arm must meet all original Program-001 absolute floors, including
95% ordering, 95% partition, 95% decision accuracy and zero recorded unsafe
authorizations/generation-limit hits. A further safeguard rejects any parsed
unsafe claim even if execution fails before the legacy safety counter is computed.

Additionally, compared with the equally trained uniform arm:

- Full-program exactness must improve by at least 0.03 (three percentage points).
- A one-sided paired sign test on family-level exact-program count differences
  must have p <= 0.05. Tied families are excluded; no discordant families gives
  p=1. Cases within a family are not treated as independent observations.
- Ordering must not degrade; decision accuracy and executed-state accuracy may
  each decline by no more than 0.01. At 128 cases this permits at most one extra
  error; at 256 it permits at most two.
- Claimed, execution-derived and independently extracted raw-claim unsafe counts
  must not increase, and the structural arm must meet its absolute zero ceilings.

These same gates apply in development and confirmation. A high-performing tie
or a control already near ceiling may yield a hold: absolute competence alone
does not demonstrate a benefit from the weighting intervention. There is one
registered training seed; the family test does not establish robustness across
training seeds or validate the synthetic generator's assumptions.

Independent per-event disposition, identifier coverage and claim completion
rates are diagnostics, not replacements for the original exact-program scores.
Null decisions and uncomputed execution safety remain visible; zero recorded
unsafe outputs is not a universal safety guarantee.

## Local preparation and tests

From this experiment directory:

```bash
python -m pytest -q tests
python run.py prepare
python run.py preflight
```

Preparation is deterministic and refuses to overwrite differing files. It
writes training/development qualification and `registration.json`, which binds
the config, Python sources, this protocol document, predecessor code dependencies,
and prepared data hashes. Preflight verifies those bindings. Changes after freeze
require a new protocol version/directory, not deleting the registration and
reusing evaluated cases. The `.run.lock` prevents concurrent top-level runners.

## Modal GPU handoff

Transfer the new directory plus the existing EDON source dependencies to the
same relative location in the Modal project. Do not replace Program-001 artifacts.
The export helper below produces a portable bundle of the bound source files
and the new prepared data, excluding all predecessor datasets and confirmations:

```bash
python bundle.py
```

Use a CUDA-enabled notebook with the pinned versions listed in `config.json`.
This package does not install or upgrade dependencies. Package versions, a
single-GPU environment, token offsets, and zero-truncation/budget checks are
enforced by the GPU workers. Token-length checks require the actual tokenizer;
CPU data qualification alone cannot certify them.

From the project root, run this in a new notebook cell:

```python
from pathlib import Path
import subprocess, sys
experiment = Path("edon/experiments/CEREBRUM-END2END-PROGRAM-002")
subprocess.run([sys.executable, "-u", "run.py", "preflight"], cwd=experiment, check=True)
subprocess.run([sys.executable, "-u", "run.py", "development"], cwd=experiment, check=True)
```

Both arms finish training before development prediction starts. Training can
resume from its last saved checkpoint. Predictions are persisted per case,
bound to their input/config/adapter hashes, and resume only the matching prefix.
Completed files cannot silently be replaced. Always use `run.py`, not concurrent
direct GPU-worker invocations.

Inspect `results/selection.json`. If and only if it reports
`READY_FOR_CONFIRMATION`, the explicit command below consumes the single reserved
confirmation evaluation for these frozen adapters:

```bash
python run.py confirmation
```

The access record is written before materialization. Interruptions can resume
the identical evaluation, but cannot select another model. Development is closed
after confirmation access. A hold leaves confirmation unmaterialized.

## Claim boundary

Even a pass is single-seed synthetic controlled-training evidence, not general
institutional intelligence, real-world transfer, deployment permission, or
production safety. `transfer_authorized` and `binding_authority` remain false.

Implementation references: Hugging Face Trainer customization and fast-tokenizer
offset mapping documentation were checked when building the custom loss. Runtime
compatibility with the pinned future-environment packages still requires the
actual Modal execution; the local CPU tests use a deterministic fake tokenizer.