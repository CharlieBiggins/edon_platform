# ACTIONNET-DATA-QUAL-013 protocol

Registered September 5, 2026 after the DEV-012 same-instrument learning curve
showed a progression from 6/32 resolved appeals at the parent, to 22/32 at step
12, to 28/32 at step 24, while the first unsafe authorization appeared at step
24.

- Training: families 700--705, seed 26090550, 24 pairs, four renderers, 192
  certificates.
- Development selection: families 720--723, seed 26090560, 16 pairs, one new
  renderer, 32 certificates.
- Untouched confirmation: families 740--747, seed 26090570, 32 pairs, one
  additional new renderer, 64 certificates.
- Every pair uses `RESOLVE_APPEAL` at exactly `clock-1` versus `clock+1`.
- Training weights are 8.0 for `ALLOW` and 9.0 for safety-critical `CONTESTED`.

The development split may select a checkpoint under the registered rule. The
confirmation split may be scored only after selection is frozen.
