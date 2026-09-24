# CEREBRUM-DEV-014-FULL

Fresh full multi-task regression of the frozen DEV-013
`continuation-step-6` adapter. There is no training in this protocol. It runs
192 checkpointed predictions: 48 each of certificate, transition, queue trace,
and pair contrast, then applies the original DEV-010 26-check gate.

```bash
python preflight.py
python run_full.py
```

The operator-reported execution passed 16/26 checks and is a full-regression
hold. Safety, pair behavior, and event partitioning remained strong, while
transition state reconstruction, queue step/final-state reconstruction, one
unresolved appeal, and one generation-limit case failed. Run
`python audit_errors.py` beside the preserved external predictions for the
case-level audit. Transfer and fresh-seed reproduction remain locked.