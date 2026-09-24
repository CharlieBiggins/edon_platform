# CEREBRUM-CLOSED-LOOP-DEV-001

Status: `READY_FOR_TWO_SEED_LEARNED_CLOSED_LOOP_DEVELOPMENT`

This package supplies the missing development environment for learned
institutional closed-loop operation. It is an executable, project-authored
synthetic curriculum rather than a protected transfer instrument.

The controller repeatedly receives a time-gated institutional observation and
may emit one non-binding operation:

```text
observe -> create goal -> plan -> allocate/dispatch -> monitor outcome
        -> replan when required -> verify -> terminate
```

Only the deterministic environment boundary accepts or rejects a proposal and
commits state. Model output cannot carry an authorization reference, execution
token, commit flag, or binding authority.

## Materialized development data

- 288 training episodes in 144 counterfactual pairs;
- 2,496 supervised training turns;
- 72 held-out development-validation episodes in 36 pairs;
- 624 label-free validation inputs with separately stored labels;
- three training institutional profiles and renderers;
- one held-out development profile and renderer;
- successful eight-cycle paths and ten-cycle failure/replanning paths;
- two registered candidate seeds: `26082491` and `26082492`.

The validation split is held out from training, but it remains internally
authored development evidence. It is not Transfer-008 and cannot support an
independent-transfer claim.

## Generate and verify

```bash
cd edon/experiments/CEREBRUM-CLOSED-LOOP-DEV-001
python generate.py
python preflight.py
python run_reference.py
python -m unittest discover -s tests -v
```

Generation is deterministic and writes LF-normalized JSON/JSONL so hashes are
stable across supported host operating systems.

## Next step

Train both registered C1 seeds using `dataset/train-turns.jsonl`, then evaluate
each frozen adapter interactively against `dataset/validation-episodes.jsonl`.
Passing reference replay or teacher-forced turn scoring is insufficient: the
learned result must run the environment sequentially without oracle access.