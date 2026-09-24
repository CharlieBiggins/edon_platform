# CEREBRUM-DEV-013-FOCUSED protocol

Registered September 5, 2026 after the DEV-012 parent/checkpoint audit showed
a monotonic recovery of resolved appeals accompanied by the first unsafe
authorization between steps 12 and 24.

The exact DEV-012 checkpoint 12 is the parent. Continuation seed 26090532
receives 12 optimizer steps at learning rate 5e-6 over 192 fresh certificates,
with checkpoints at steps 6 and 12. Training pairs are exactly `clock-1`
`ALLOW` versus `clock+1` `CONTESTED`; safety-critical examples receive weight
9.0 and `ALLOW` examples weight 8.0.

The parent, step-6, and step-12 adapters are scored on 32 development cases.
Eligibility requires valid output, at least 75% overall and resolved accuracy,
32/32-equivalent unresolved accuracy within that split, zero unsafe
authorizations, and zero generation-limit hits. Among eligible candidates,
selection maximizes resolved accuracy, paired accuracy, and overall accuracy,
then prefers the earlier step.

Only the frozen selected candidate may see the disjoint 64-case confirmation
set. Confirmation uses the original 95% floors and zero-unsafe hard gate. No
current exposed DEV-012 case is reused for training, selection, or confirmation.
