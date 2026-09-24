# CEREBRUM-DEV-017-CAUSAL

DEV-017 tests whether the stable DEV-016 failure signature was caused partly by
incomplete curriculum exposure. DEV-016 consumed only 192 effective samples
from a 368-record dataset and both checkpoints retained the same 12 failures.

DEV-017 returns to the frozen DEV-015 checkpoint-12 adapter and performs one
complete, low-learning-rate pass over 384 fresh causal-chain records. With
effective batch 16 and 24 optimizer steps, the registered exposure count is
exactly 384. Checkpoints 12 and 24 are scored on 64 fresh development cases.
Only a checkpoint passing all 26 checks, including zero unsafe
authorizations, can open the new 192-case confirmation.

DEV-016 remains a frozen negative result. Its adapters are not continued, and
its development or confirmation cases are not used for training.

## Frozen result

The September 6, 2026 GPU run rejected both checkpoints. Step 12 passed 18/26
full-regression checks with 14 failing cases; step 24 passed 18/26 with 13
failing cases. Both made two unsafe authorizations. Thirteen failures were
shared, dominated by delayed evidence, approval withdrawal, and unresolved
appeal handling. The confirmation remained sealed.

This falsifies the proposed incomplete-exposure explanation for the stable
DEV-016 error signature. DEV-017 is frozen as a negative result and is not a
basis for another additive LoRA continuation.
