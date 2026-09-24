# ACTIONNET-DEV-DATASET v1.0.0 Data Card

## Purpose

Internal development data for testing a Cerebrum preprocessing, tokenization, LoRA, checkpoint, and evaluation pipeline. It is not confirmatory training data.

## Composition

- 720 examples.
- 360 paired trajectories.
- 480 train examples.
- 120 development examples.
- 120 public-holdout inputs with separately stored labels.
- 240 pivotal pairs, 60 actor-renaming invariance pairs, and 60 contextually dominated non-pivotal pairs.
- Eight intervention families.
- Six semantic states and five decision outcomes.
- Formal, event-log, and memo renderers.

## Generation and verification

Every trajectory begins from a typed finite institutional state. Matched events are applied through two separately implemented transition and evaluation engines. Disagreement raises an error and prevents release. Canonical trajectories retain initial state, event, intervention, final state, paths, consequences, trace hash, and renderer hashes. Model-facing records contain only an opaque case identifier, institution lineage, rendered observation, and query.

## Splits

Train, development, and public holdout are disjoint by institution lineage, semantic family, generator lineage, domain label, selected renderer, and model-input hash. Four additional semantic families and two domain slots are reserved but not materialized.

## Known limitations

- Fully synthetic and not source-grounded.
- Generator, both reference engines, renderers, and oracle share project authorship.
- Domain names are vocabulary skins, not domain validation.
- Institution families vary registered finite parameters rather than natural institutional source structures.
- A transparent symbolic system can recover much of the decision function from the explicit typed factors; success on this corpus cannot establish cross-institution learning.
- No independent human domain review.
- No transformer tokenizer or LoRA run is part of this result.

## Permitted use

Development pipeline testing, ablation design, leakage testing, mechanism-sensitive evaluation development, and non-confirmatory LoRA smoke training.

## Prohibited interpretation

The dataset must not be represented as evidence that Cerebrum learned from ActionNet, generalized to real institutions, acquired a foundation representation, or is safe for institutional deployment.