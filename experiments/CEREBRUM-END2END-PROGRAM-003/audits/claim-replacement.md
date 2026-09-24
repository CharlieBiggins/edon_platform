# Program-002 claim-replacement diagnostic

Date: September 8, 2026. This diagnostic is not a new learned-model score.
The reproducible CPU helper is `../diagnose_claims.py`; full case-level results
and input/prediction/score hashes are in `claim-replacement.json`.

Original uploaded evidence: `prism-uploads/development.jsonl`, both
`development-*-predictions_2.jsonl` files, and both `development-*-score.json`
files. Both prediction hashes and the input hash match the saved score bindings.
Original per-case evaluations were replayed exactly before the ablation.

The procedure parses each original program twice, runs its UNCHANGED steps
through both interpreters, checks agreement, then replaces only its state and
certificate claims in an in-memory copy with the execution-derived values.
It does not use oracle states or certificates to construct those replacements.
Original source oracles are used only in scoring. No event sorting, ID repair,
disposition repair, missing-event insertion, or output-file replacement occurs.

| Metric, out of 128 | Uniform original | Uniform diagnostic | Structural original | Structural diagnostic |
|---|---:|---:|---:|---:|
| Full program exact | 115 | 118 | 115 | 120 |
| Decision correct | 124 | 126 | 121 | 126 |

This isolates three uniform and five structural failures attributable solely
to inconsistent claims. It does not fix every remaining program. In particular,
the uniform arm has an evidence-expiry execution error whose original raw claim
was correctly DENY but whose executed program derives ALLOW. Claim replacement
therefore turns that case into an unsafe ALLOW claim in the diagnostic; the
program is still rejected. Mechanically consistent claims are not necessarily
correct if the underlying steps are wrong.

Both diagnostic arms remain below the event-order/partition floors; the uniform
diagnostic also retains an unsafe execution-derived authorization. These results
do not authorize either adapter, reopen confirmation, or replace the original
Program-002 DEVELOPMENT_HOLD. Program-003 must still learn temporal boundaries,
coverage/order, state changes, and certificate derivation.