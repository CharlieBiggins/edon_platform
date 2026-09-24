# CEREBRUM-TRANSFER-008

This directory reserves the next fresh two-seed zero-shot transfer protocol for
the compute-bounded `CEREBRUM-DEV-009-RB1` candidates.

`AMENDMENT-001-BASELINE-FAIRNESS.md`, frozen on 2026-09-01 before any
instrument materialization, adds raw, interface-matched, and prompted
interface-matched Qwen conditions. The primary learned comparison uses the
stronger matched condition; the raw unmodified condition remains diagnostic.
The original Scope-001-anchored manifest, reservation, and gate bytes are
unchanged.

Current status:

`RESERVED_BLOCKED_PENDING_RB1_TWO_SEED_PASS_AND_INDEPENDENT_INSTRUMENT`

Observed prerequisite disposition on September 4, 2026:
`RB1_TRANSFER_NOT_ESTABLISHED`. The frozen reservation therefore remains
unmaterialized and is closed to candidate substitution. A future DEV-010 pass
would require a new transfer identity and fresh instrument.

The shell is intentionally incomplete. It contains no transfer cases, prompts,
labels, oracle, independent generator, prediction runtime, predictions, scorer,
or protected outcome. Those artifacts may be constructed only after:

1. both registered RB1 seeds are frozen;
2. `score_rb1.py` reports
   `COMPUTE_BOUNDED_SYNTHETIC_TRANSFER_REPRODUCED`;
3. both adapter identities and hashes are registered;
4. the learned baseline registry and public interface prompt pack are frozen;
5. an independent custodian supplies matching candidate, baseline, prompt-pack,
   and fresh instrument commitments;
6. the materialization authorization gate passes.

Transfer-008 cannot revive, rescore, or reuse Transfer-003, Transfer-006,
Transfer-007, DEV-009 lite, or RB1 development cases. It is zero-shot: no
training, prompt repair, adapter update, case-specific parsing patch, or
threshold tuning may use Transfer-008 material.

## Shell validation

```bash
cd edon/experiments/CEREBRUM-TRANSFER-008
python preflight.py
python -m unittest discover -s tests -v
```

Expected status:

`SHELL_READY_MATERIALIZATION_UNAUTHORIZED_PENDING_RB1_PASS`

Passing this shell preflight is infrastructure evidence only. It is not a
transfer result and does not authorize predictions or scoring.