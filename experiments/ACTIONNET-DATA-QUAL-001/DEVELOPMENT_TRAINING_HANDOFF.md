# Development LoRA Handoff

Disposition required: `READY_FOR_DEVELOPMENT_TRAINING`.

## Allowed files

- Training: `dataset/train.jsonl`
- Model selection and debugging: `dataset/development.jsonl`
- Public evaluation input: `dataset/public_holdout_inputs.jsonl`

The supervised pipeline must use only `input` as model input and `target` as supervision. `metadata` is audit information and must not be serialized into prompts or features.

## Forbidden files during model development

- `oracle/public_holdout_labels.jsonl`
- `oracle/canonical_trajectories.jsonl`
- `oracle/protected_reservation.json`

Public-holdout labels may be accessed only by a scoring process after predictions are frozen. Protected families and domains remain unmaterialized.

## Required development comparisons

1. Unmodified base model.
2. ActionNet LoRA.
3. Same architecture and token budget without ActionNet trajectories.
4. Transparent rules baseline.
5. Retrieval or prompted baseline if used in the eventual protected study.

## Required evaluations

- decision and semantic-state accuracy;
- unsafe authorization and dangerous omission;
- pivotal-pair sensitivity;
- invariance-pair consistency;
- contextual non-pivotal stability;
- renderer transfer from formal/event-log views to memo views;
- calibration and abstention;
- certificate field validity;
- public-input leakage audit.

Any development result remains internal and non-confirmatory. Protected EDON-LT execution requires new independently constructed institutions, source lineages, custody records, frozen runtimes, and a new result identity.