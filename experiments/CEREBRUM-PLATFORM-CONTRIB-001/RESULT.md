# Current result

## Transparent proxy

Status: `PROXY_SIGNAL_ESTABLISHED`.

| Metric | Control | Platform 002 | Difference |
| --- | ---: | ---: | ---: |
| Decision accuracy | 79.69% | 100.00% | +20.31 points |
| Risk-band accuracy | 72.81% | 100.00% | +27.19 points |
| Capacity-band accuracy | 93.12% | 96.25% | +3.12 points |
| Joint accuracy | 62.81% | 96.25% | +33.44 points |
| Risk MAE | 0.0944 | 0.0218 | -0.0726 |
| Unsafe authorizations | 0 | 0 | 0 |

This result demonstrates that the matched instrument detects information found
in Platform 002 compositions and counterfactuals. Because the model is a
transparent proxy and the target remains project-authored synthetic, it does
not establish the registered Cerebrum contribution claim.

## Qwen/Cerebrum

Status: `NOT_EXECUTED_BLOCKED_MISSING_QWEN_GPU_AND_FRESH_TARGET_CUSTODY`.

No adapter, Qwen prediction, or protected Qwen score exists.