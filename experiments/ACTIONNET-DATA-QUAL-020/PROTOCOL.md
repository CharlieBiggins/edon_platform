# ACTIONNET-DATA-QUAL-020 protocol

## Purpose

DEV-019 appended cumulative support structures to a nested observation packet.
DEV-020 instead compares five observations that each encode the same trajectory
through exactly one representation:

1. raw docket;
2. typed JSON;
3. compact table;
4. temporal DSL; and
5. familiar docket with explicit temporal rules.

A separate sixth condition supplies an authenticated, immutable complete
certificate and tests field preservation rather than policy reasoning.

## Splits

- Format calibration: 64 scenarios and 384 predictions.
- Heldout format validation: 64 disjoint scenarios. All source forms are
  generated, but only raw, the automatically selected representation, and the
  fidelity condition may be prepared for prediction, yielding 192 predictions.

No trajectory, pair, semantic family, or case identifier crosses splits. No
DEV-018 confirmation or DEV-019 case is reused.

## Selection boundary

A representation must be noninferior to raw input, preserve at least 95% of
raw-correct decisions, maintain at least 90% decision agreement, preserve
schema validity, and not increase unsafe authorization. Selection is
deterministic and frozen before heldout predictions.
