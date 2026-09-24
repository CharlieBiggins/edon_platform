# CEREBRUM-DEV-020-INTERFACE-CALIBRATION

DEV-020 performs no training. It first freezes an offline audit of DEV-019,
then evaluates the unchanged DEV-017 checkpoint 24 on five direct observation
representations and one authenticated immutable-certificate condition.

The calibration split selects at most one candidate using registered paired
noninferiority and safety gates. Only then are raw, selected, and fidelity
conditions opened on 64 disjoint heldout scenarios.

A pass validates an interface for future native training. It does not show that
Cerebrum learned exact execution and does not authorize transfer or deployment.

After a completed run, `finalize_result.py` performs a CPU-only integrity
freeze and emits a scenario-level audit of every remaining heldout failure. It
does not run inference or alter the frozen calibration/validation results:

```bash
python -u finalize_result.py
```
