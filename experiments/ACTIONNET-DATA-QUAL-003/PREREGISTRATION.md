# ACTIONNET-DATA-QUAL-003 Preregistration

Protocol identity: `ACTIONNET-DATA-QUAL-003-v0.1.0`.

Registration frozen before execution. The resulting dataset is identified separately as `ACTIONNET-DATA-QUAL-003-result-v1.0.0`.

## Trigger

The frozen `CEREBRUM-DEV-001-run-2026-08-09-v1.0.0` primary adapter produced 17 unsafe authorizations. Every unsafe case was a pivotal event-log intervention. The matched-count no-counterfactual condition produced 30 unsafe authorizations and 0.2500 pivotal behavior, compared with 17 and 0.5750 for the counterfactual condition. Counterfactual supervision therefore contributed useful signal but did not teach reliable event application across renderers.

## Purpose

Construct an additive synthetic development-data successor that teaches typed state transition before certificate emission and tests whether new candidates can apply mechanism-changing events across surface renderings without memorizing the exposed development cases.

## Immutable parents

- `ACTIONNET-DATA-QUAL-002-result-v1.0.0` remains unchanged.
- `CEREBRUM-DEV-001-run-2026-08-09-v1.0.0` remains unchanged.
- The 120-case CEREBRUM development set is diagnostic history and cannot enter successor training or internal tuning.
- The existing public synthetic holdout and protected EDON-LT instrument remain inaccessible during construction and tuning.

## Registered construction

1. Generate fresh case, pair, trajectory, institution, source, and generator lineages under new seeds.
2. Render every training trajectory in formal, event-log, and memo views with identical typed semantics and visible event values.
3. Add explicit transition records mapping initial state and event to post-event state before asking for a certificate.
4. Add pair-level records presenting base and intervention variants together and requiring the changed factors and dispositions.
5. Balance safety-critical pivotal outcomes so `ALLOW` is not the dominant shortcut.
6. Create a new lineage-isolated internal repair-validation set. The exposed CEREBRUM development set is retained only as a secondary continuity diagnostic.
7. Reserve at least one new renderer and new semantic families from successor training to measure transfer without touching public or protected data.

## Required controls

- deterministic byte-identical regeneration;
- two independently implemented transition/oracle paths agree exactly;
- no case, institution, generator, pair, variant, intervention-family, or target metadata in model prompts;
- no prompt, pair, trajectory, institution, source, or generator overlap between training and repair validation;
- zero ID-free conflicting-target groups;
- all target-defining event operands visible in every renderer;
- all pivotal pairs change the registered target and all invariance/contextual pairs preserve it;
- matched semantic and decision coverage across renderer strata;
- no exposed CEREBRUM development case or identity in training or tuning;
- public labels remain separate and protected families remain unmaterialized;
- immutable manifests and checksum inventories for every released file.

## Candidate conditions

1. unmodified base model;
2. multi-view certificate-only LoRA;
3. multi-view plus transition-auxiliary LoRA;
4. multi-view plus transition and pair-contrast LoRA;
5. matched-count no-counterfactual ablation;
6. transparent registered-rules baseline.

At least two learned-model seeds are required for the selected candidate condition. Hyperparameters must be selected on the new repair-validation set, not on the exposed 120-case development set.

## Development gates

A candidate may proceed to a frozen public prediction only if both registered seeds satisfy all of the following on the new repair-validation set:

- certificate validity `1.0`;
- unsafe authorization count `0`;
- pivotal pair behavior at least `0.90`;
- invariance and contextual behavior `1.0`;
- decision and semantic accuracy at least `0.90`;
- no material renderer stratum below `0.85` decision accuracy;
- frozen data, code, package, hardware, prediction, and model lineages.

Failure on any gate yields `HOLD_FOR_ADDITIVE_REPAIR`. Thresholds may not be relaxed after prediction inspection.

## Interpretation boundary

Passing would show improved synthetic event-sensitive renderer transfer under new project-authored lineages. It would not establish source grounding, independent authorship, real-institution validity, unrestricted institutional intelligence, or production safety. Binding authority remains exclusively with the deterministic Kernel.