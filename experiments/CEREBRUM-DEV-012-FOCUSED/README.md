# CEREBRUM-DEV-012-FOCUSED

Compute-minimal additive successor to the DEV-011 seed-26090512 near-miss. It
continues that exact adapter for 24 optimizer steps on 384 fresh, balanced,
symmetrically weighted appeal-finality certificates and scores 64 fresh cases.

```bash
python preflight.py
python run_focused.py
```

Training and prediction are resumable. Checkpoints are written every 12 steps.

The September 5, 2026 operator-reported run completed but passed only 4/9
focused gates. It reached 59/64 decisions, including 28/32 resolved appeals and
31/32 unresolved appeals, with one unsafe authorization. Same-instrument
diagnostics showed the DEV-011 parent at 38/64, DEV-012 checkpoint 12 at 54/64
with zero unsafe authorizations, and the final checkpoint at 59/64 with one
unsafe authorization. All five final errors were localized to `clock-1` or
`clock+1` appeal-resolution cases.

The result is `FOCUSED_BALANCE_REPAIR_HOLD`. Full regression and transfer
remain locked.