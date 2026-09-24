# ActionNet Matched-002 — locked paired-seed qualification

Status: `IMPLEMENTED_DRAFT_NOT_REGISTERED`.

This successor freezes the cheapest broader Stage-1 test: 48 fresh cases in 24
counterfactual pairs, answered once by Ordinary A, ActionNet A, Ordinary B and
ActionNet B (192 responses). It performs no new training. Seed B is trained by a
separately registered Matched-001 replication run whose study changes only
`training_seed_label` from `A` to `B`.

The instrument is project-authored confirmation, not independent transfer. It is
generated from new registered family ranges only after reconstructing the frozen
predecessor exposure closure and the Matched-001 data. Both seed-pair advantages
must pass; an aggregate win cannot hide a seed reversal.

Typical CPU setup:

```sh
python -B edon/experiments/CEREBRUM-ACTIONNET-MATCHED-002/run.py preflight
python -B edon/experiments/CEREBRUM-ACTIONNET-MATCHED-002/run.py prepare-instrument \
  --output-dir matched002-instrument
```

Resolve `study.template.json`, register both Matched-001 run registrations, and
bind the instrument before seed-B training or any broader seed-A evaluation.
GPU inference is intentionally a separate, explicit paid command:

```sh
python -B edon/experiments/CEREBRUM-ACTIONNET-MATCHED-002/predict.py \
  --run-dir matched002-run --candidate actionnet-a --candidate-run matched001-a-run \
  --arm actionnet --base-snapshot qwen3-4b-snapshot --authorize-paid
```

The base snapshot is never downloaded by this package. All four prediction files
must exist before one locked `score` transaction. This framework does not grant
transfer, deployment or binding authority.