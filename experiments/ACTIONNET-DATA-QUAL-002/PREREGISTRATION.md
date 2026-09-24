# ACTIONNET-DATA-QUAL-002 Preregistration

Result identity: `ACTIONNET-DATA-QUAL-002-result-v1.0.0`.

This additive successor preserves ACTIONNET-DATA-QUAL-001 and repairs two construct-validity failures found before GPU training:

1. the memo renderer omitted event values, creating ID-free identical observations with different targets;
2. malformed initial state could determine `INVALID` without an observable malformed field.

The successor must retain all registered counts, pair classes, split separation, dual-engine agreement, semantic coverage, label separation, and deterministic generation. In addition, it requires zero ID-free conflicting-target groups, observable malformed conditions, visible memo event values, model-facing inputs without case or institution identifiers, and ID-free prompt-hash separation.

Passing creates `READY_FOR_DEVELOPMENT_TRAINING_OBSERVABLE`. It remains synthetic, same-project authored, non-source-grounded, and non-confirmatory.