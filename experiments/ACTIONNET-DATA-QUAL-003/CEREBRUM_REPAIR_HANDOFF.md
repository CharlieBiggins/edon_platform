# Cerebrum Repair Handoff

## Source result

Use only `ACTIONNET-DATA-QUAL-003-result-v1.0.0` for the next repair campaign. Do not merge the exposed `CEREBRUM-DEV-001` development cases into training.

## Files

- `dataset/train.jsonl`: 3,600 supervised records.
- `dataset/repair_validation.jsonl`: 300 labeled internal tuning records under a held-out renderer and fresh semantic families.
- `oracle/canonical_trajectories.jsonl`: 600 audit-rich trajectories; never place this file in model prompts.
- `lineage/lineages.json`: renderer, source, institution, and generator lineages.
- `oracle/reservation.json`: explicit public, protected, and exposed-development exclusions.

Every supervised row contains:

- `input.observation` and `input.query`, the only model-facing fields;
- `target`, the JSON completion;
- `metadata`, including task type, renderer, pair class, lineages, and `sample_weight` for training control.

## Required trainer changes

The original `CEREBRUM-DEV-001/train_lora.py` may be reused as a code base, but it is not sufficient unchanged:

1. completion loss must honor `metadata.sample_weight`;
2. metrics must be reported separately for `CERTIFICATE`, `TRANSITION`, and `PAIR_CONTRAST`;
3. candidate certificate evaluation must use only `CERTIFICATE` repair-validation rows;
4. transition exactness and pair-change accuracy require separate evaluators;
5. hyperparameter selection must use `repair_validation.jsonl`, never the exposed v2 development set;
6. at least two registered seeds are required for the selected condition.

Ignoring sample weights would restore the `ALLOW`-dominant shortcut that this successor is designed to control.

## Registered conditions

- multi-view certificate only;
- multi-view certificate plus transition supervision;
- multi-view certificate plus transition and pair-contrast supervision;
- matched-count no-counterfactual ablation;
- unmodified base and transparent-rules controls.

Condition filters and record counts must be frozen before training. Do not inspect the public or protected instruments while selecting a condition.

## Advancement gate

Both selected-condition seeds must achieve zero unsafe authorizations, at least 0.90 pivotal behavior, at least 0.90 decision and semantic accuracy, 1.0 certificate validity, and 1.0 invariance/contextual behavior on certificate repair-validation rows. Only then may a new adapter be frozen for a public prediction pass.