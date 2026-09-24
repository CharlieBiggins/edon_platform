# CEREBRUM-DEV-013-FOCUSED

Safety-constrained near-clock successor to the DEV-012 learning-curve audit.
It starts from the safe DEV-012 checkpoint 12, trains for 12 additional steps,
and compares the parent, step-6, and step-12 candidates on a fresh 32-case
development split.

Only candidates with exact unresolved-side performance and zero unsafe
authorizations are eligible. The selector then maximizes resolved accuracy,
paired-boundary accuracy, and overall accuracy, breaking ties toward the
earlier checkpoint. The selected candidate receives one 64-case untouched
confirmation score.

```bash
python preflight.py
python run_focused.py
```

Training and predictions are resumable. The operator-reported run selected
step 6 after both continuation checkpoints scored 32/32 on development. The
single-use confirmation scored 63/64, including 32/32 unresolved cases, with
zero unsafe authorizations and all 9 focused checks passing. This remains a
single-candidate focused signal; full multi-task regression is mandatory.
