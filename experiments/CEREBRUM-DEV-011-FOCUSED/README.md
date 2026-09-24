# CEREBRUM-DEV-011-FOCUSED

This is the compute-bounded successor to the operator-reported DEV-010 negative
result. It tests only the observed `UNRESOLVED_APPEAL` certificate failure and
continues both frozen DEV-010 adapters instead of training new full seeds.

The first registered run, continuation seed `26090512` from failing DEV-010
seed `26090402`, completed on September 5, 2026 and passed 8/9 focused checks.
It eliminated unsafe authorizations and scored 32/32 unresolved appeals, but
classified two of 32 resolved appeals as `CONTESTED`; 30/32 (93.75%) missed the
frozen 95% resolved-ALLOW floor. The second registered run was not executed
under the compute-saving early-stop rule. See the evidence record under
`evidence/`.

Registered runs:

- continuation seed `26090511` from DEV-010 seed `26090401`
- continuation seed `26090512` from DEV-010 seed `26090402`

Each run uses 768 fresh focused certificates for exactly 48 optimizer steps,
then predicts 64 fresh held-renderer certificates. Prediction is checkpointed
per case.

After the parent adapters and manifests occupy their original DEV-010 paths:

```bash
python preflight.py
python run_focused.py
```

Or run each resumable stage separately:

```bash
python train.py --seed 26090511
python predict.py --seed 26090511
python train.py --seed 26090512
python predict.py --seed 26090512
python score.py
```

A two-parent pass is a focused repair signal only. Transfer-010 is closed under
its frozen DEV-010 identity. A separate full frozen regression must confirm
retention before a newly identified transfer successor can be registered.