# ActionNet Matched-001 — token-matched development framework

Built September 19, 2026. Status:
`IMPLEMENTED_DRAFT_NOT_REGISTERED`.

This package implements the cheapest A-stage experiment described in `CONTRACT.md`:
fresh Ordinary A and ActionNet A adapters from the same pinned Qwen3-4B base,
the same underlying scenario pool, the same native-program evaluation output,
and a matched processed-non-padding-token budget. It does not contain a learned
result and does not authorize GPU spending, transfer, deployment, or binding
institutional action.

The same immutable training engine can create a separately registered seed-B
replication run by changing only `training_seed_label` from `A` to `B` in a new
study before registration. The numeric B seed is already frozen in `config.json`.

Ordinary receives one native-program example for each scenario. ActionNet
receives those byte-identical native examples plus execution-trace examples and
one explicit causal-relation example per complete counterfactual pair. The token
planner selects only complete pair groups, requires one complete traversal in
each arm, and rejects a realized arm difference above the approved tolerance.
The arms can therefore differ in optimizer-step count and task-token mixture;
those quantities are reported and are not called matched.

The framework deliberately has no network downloader or package installer.
Token planning and GPU execution require an operator-supplied, read-only local
base snapshot whose model and tokenizer tree hashes match the approved study.
All outputs use new directories or append immutable stage files; registered
evidence is never overwritten.

## Commands

From the workspace root:

```sh
python -B edon/experiments/CEREBRUM-ACTIONNET-MATCHED-001/run.py preflight
python -B -m unittest discover -s edon/experiments/CEREBRUM-ACTIONNET-MATCHED-001/tests -v
```

After Program-005 is complete, locally restored, and worth auditing:

```sh
python -B edon/experiments/CEREBRUM-ACTIONNET-MATCHED-001/run.py audit-program005 \
  --workspace restored005 --parent-search restored-parent --output-dir audit005-final
```

After copying `study.template.json` to a new decision file and resolving its
commitments, materialize a new run directory:

```sh
python -B edon/experiments/CEREBRUM-ACTIONNET-MATCHED-001/run.py prepare \
  --study matched001-study.json --program005-audit audit005-final/program005-audit.json \
  --output-dir matched001-a-run

python -B edon/experiments/CEREBRUM-ACTIONNET-MATCHED-001/run.py token-plan \
  --run-dir matched001-a-run --base-snapshot qwen3-4b-snapshot

python -B edon/experiments/CEREBRUM-ACTIONNET-MATCHED-001/run.py register \
  --run-dir matched001-a-run
```

`prepare` is CPU-only and reconstructs registered predecessor exposures before
generating new family ranges. `token-plan` loads only the supplied tokenizer.
`register` refuses unresolved registration approvals, hashes, budgets, gates, or
mismatched token plans. None of these commands trains or predicts. Paid approval
is a subsequent immutable act: copy `execution-approval.template.json`, bind it
to the printed registration/study hashes and exact registered caps, then run:

```sh
python -B edon/experiments/CEREBRUM-ACTIONNET-MATCHED-001/run.py authorize-execution \
  --run-dir matched001-a-run --approval matched001-execution-approval.json
```

Paid stages require both the frozen study approval and the literal CLI flag:

```sh
python -B edon/experiments/CEREBRUM-ACTIONNET-MATCHED-001/run.py runtime \
  --run-dir matched001-a-run --base-snapshot qwen3-4b-snapshot --authorize-paid
python -B edon/experiments/CEREBRUM-ACTIONNET-MATCHED-001/run.py train \
  --run-dir matched001-a-run --base-snapshot qwen3-4b-snapshot --arm ordinary --authorize-paid
python -B edon/experiments/CEREBRUM-ACTIONNET-MATCHED-001/run.py train \
  --run-dir matched001-a-run --base-snapshot qwen3-4b-snapshot --arm actionnet --authorize-paid
python -B edon/experiments/CEREBRUM-ACTIONNET-MATCHED-001/run.py predict \
  --run-dir matched001-a-run --base-snapshot qwen3-4b-snapshot --arm ordinary --authorize-paid
python -B edon/experiments/CEREBRUM-ACTIONNET-MATCHED-001/run.py predict \
  --run-dir matched001-a-run --base-snapshot qwen3-4b-snapshot --arm actionnet --authorize-paid
python -B edon/experiments/CEREBRUM-ACTIONNET-MATCHED-001/run.py record-billing \
  --run-dir matched001-a-run --receipt matched001-billing-receipt.json
python -B edon/experiments/CEREBRUM-ACTIONNET-MATCHED-001/run.py score \
  --run-dir matched001-a-run --output-dir matched001-a-score
```

Copy `billing-receipt.template.json` after Lightning AI (or Modal) supplies the actual
A-stage GPU hours and cost. Final scoring rejects unregistered retry/result files
and refuses to substitute runner estimates for provider billing evidence.

The 24-case, 48-response result is an adaptive development screen only. The
scorer returns `SUPPORTED`, `NOT_SUPPORTED`, or `INCONCLUSIVE` only for a
complete valid screen. `SUPPORTED` permits designing the broader four-model
qualification; it is not transfer, production-verifier, customer-value, or
mini-IGI evidence. Reference-assisted scoring uses hidden answers offline and
must never be represented as a deployable verifier.

## Remaining execution blockers

- A verified final Program-005 audit and acknowledged frozen disposition.
- Actual base/tokenizer snapshot hashes and license review.
- Approved token, GPU-hour, and currency caps.
- Explicit registration and paid-execution identities/dates.
- Review of the proposed numerical screen gates for the 24-case screen.
- A real L4 runtime rehearsal. CPU tests do not establish GPU readiness.

Seed B, a broader protected instrument, transfer, closed loop, and customer
pilot remain separately registered future stages.