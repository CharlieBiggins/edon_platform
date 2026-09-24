# CEREBRUM-PLATFORM-CONTRIB-001

This experiment tests whether ActionNet Platform 002 active experience adds
learnable value beyond count-matched single-mechanism experience.

## Current status

`PROXY_SIGNAL_ESTABLISHED_CONFIRMATORY_QWEN_BLOCKED`

The complete transparent proxy diagnostic has been executed. The Platform 002
condition improves over the matched control by:

- 20.31 percentage points in decision accuracy;
- 27.19 points in risk-band accuracy;
- 33.44 points in joint decision/risk/capacity accuracy;
- 0.0726 lower risk-score mean absolute error;
- zero unsafe authorizations in both conditions.

This is useful pipeline and representation evidence, but it is **not a
Cerebrum result**. The proxy uses a transparent linear interaction model. No
Qwen weights were loaded or trained locally.

## Frozen learned experiment

The package includes matched 800-record control and Platform 002 training
conditions, a separately implemented 320-case orbital-launch-range diagnostic,
two registered Qwen seeds per condition, QLoRA training and prediction scripts,
prediction freezing, and a single-use scorer.

The proxy score opened those 320 labels. Consequently, the same target is now
eligible only for Qwen development rehearsal—not confirmatory Cerebrum
evidence. A fresh independently custodied target must be created after model
predictions are frozen for the actual milestone.

Local confirmatory preflight is correctly blocked for two reasons: this
workspace has no CUDA/ML runtime, and no fresh independently custodied target
has been supplied.

```bash
python verify_package.py
python preflight.py
```

See `GPU_EXECUTION.md` to run the four registered adapters externally.