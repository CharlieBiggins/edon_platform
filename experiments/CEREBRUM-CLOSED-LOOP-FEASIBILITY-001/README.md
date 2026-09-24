# Cerebrum closed-loop feasibility 001

Status: `IMPLEMENTED_DEVELOPMENT_FEASIBILITY_NOT_REGISTERED`.

This package materializes the proposed inexpensive 12-episode feasibility test
from the existing public synthetic closed-loop generator. It does not touch a
protected transfer instrument or real institutional data.

The suite contains three episodes of each type:

1. normal governed completion;
2. a recoverable deterministic Kernel rejection followed by revision/retry;
3. delayed or conflicting observed evidence;
4. failed outcome, monitoring and replanning.

The two frozen ActionNet candidates are evaluated separately. A limited
rules-only controller and an oracle reference replay are different controls:
the reference proves solvability, while the limited controller is the actual
comparison baseline. Model proposals never commit state directly.

```sh
python -B edon/experiments/CEREBRUM-CLOSED-LOOP-FEASIBILITY-001/run.py preflight
python -B edon/experiments/CEREBRUM-CLOSED-LOOP-FEASIBILITY-001/run.py prepare \
  --output-dir closed-loop-12
python -B edon/experiments/CEREBRUM-CLOSED-LOOP-FEASIBILITY-001/run.py run-reference \
  --run-dir closed-loop-12 --output reference.json
python -B edon/experiments/CEREBRUM-CLOSED-LOOP-FEASIBILITY-001/run.py run-baseline \
  --run-dir closed-loop-12 --output baseline.json
```

`model_runner.py` performs explicit paid local inference from a pinned base and
one trained adapter. Twelve episodes are only a feasibility signal; a pass calls
for a separately frozen 24–48 episode qualification before a strong external
operational claim.