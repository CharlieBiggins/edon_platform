# CEREBRUM-DEV-015-MIXED

Compute-bounded mixed multi-task retention repair after DEV-014 passed safety
but failed transition and queue-state reconstruction. It continues the frozen
DEV-013 step-6 adapter for 24 steps with 384 replay records emphasizing
transition and queue trace while retaining broad certificates, near-clock
appeals, pair contrast, queue order, and queue partition.

Checkpoints 12 and 24 are evaluated on 64 fresh four-task cases. Only
a checkpoint passing all 26 checks may open the single-use 192-case full
confirmation.

```bash
python preflight.py
python run_mixed.py
```

DEV-014 validation cases are never used for training. Transfer remains locked.

## Operator-reported result — 2026-09-06

Both checkpoints passed 23/26 development checks. Queue exactness reached 75%
and transition exactness 81.25%, but each checkpoint retained one
delayed-evidence unsafe authorization, scored 5/6 on pivotal certificates, and
reconstructed 14/16 transition post-states. No checkpoint was selected and the
192-case confirmation remained sealed.