# ACTIONNET-DATA-QUAL-001 Preregistration

Result identity: `ACTIONNET-DATA-QUAL-001-result-v1.0.0`.

## Registered release

- 720 examples forming 360 base/intervention pairs.
- 480 train, 120 development, and 120 public-holdout examples.
- Institution, semantic-family, generator, domain, and selected-renderer separation.
- Four protected semantic families reserved but not materialized.

## Required gates

1. Zero reference-engine disagreement.
2. Zero transition disagreement.
3. The corpus contains 240 pivotal pairs, 60 invariance pairs, and 60 contextually dominated non-pivotal pairs.
4. Pivotal pairs change disposition; invariance and contextual pairs do not.
5. Pivotal and contextual pairs use matched single-event controls; invariance pairs differ only by actor renaming.
6. All six semantic states and five decision outcomes occur.
7. Every registered intervention family has nonzero coverage.
8. No forbidden answer fields or decision labels occur in model-facing inputs or identifiers, and public inputs contain no audit metadata.
9. No exact duplicate model inputs occur across examples.
10. Institution, semantic-family, generator, domain, and prompt hashes are split-disjoint.
11. The public-holdout selected renderer is absent from training.
12. Public-holdout labels remain in a separate oracle artifact.
13. Protected families, domains, and seeds remain unmaterialized.
14. A repeated generation call is byte-deterministic.

Passing creates `READY_FOR_DEVELOPMENT_TRAINING`. Confirmatory readiness remains false because the generator, engines, renderers, cases, and oracle share project authorship and are not source-grounded.