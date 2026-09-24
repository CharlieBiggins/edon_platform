# ACTIONNET-DATA-QUAL-005 Protocol Specification

Protocol identity: `ACTIONNET-DATA-QUAL-005-v0.1.0`  
Result identity: `ACTIONNET-DATA-QUAL-005-result-v1.0.0`  
Date frozen: 2026-08-12

## Purpose

Create a fresh, synthetic, compact-target EventNet corpus for a separate CEREBRUM-DEV-004 repair experiment. The package is additive to ActionNet-004 and cannot change any DEV-003 artifact or score.

## Registered generation

- Training seed: `26081205`.
- Validation seed: `26081206`.
- Training families: 70--81, 20 pairs per family.
- Validation families: 90--93, 15 pairs per family.
- Training domains: licensing, grants, and records.
- Validation domains: benefits administration and infrastructure administration.
- Training renderers: `FORMAL`, `EVENT_STREAM`, `CASE_DOCKET`.
- Validation renderer: `AUDIT_PACKET`.

The registered counts are 5,040 training records, 420 validation records, 600 trajectories, and 300 counterfactual pairs.

## Compact target rule

Certificate targets remain complete. Transition targets contain predicted post-state and semantic fields. Queue targets contain order, execution/defer lists, compact step semantics, and final state. Pair targets contain both certificates plus causal and post-state change paths. No language-model target contains a cryptographic state hash; hashes are derived downstream from predicted states.

## Qualification controls

All registered controls in `actionnet_eventnet.py` must pass, including independent scheduler/transition agreement, pivotal/invariance/context behavior, all mechanism coverage, prompt-label hygiene, train/validation lineage disjointness, ActionNet-004 case/prompt non-overlap, renderer holdout, deterministic generation, and unmaterialized reserved families.

## Claim boundary

Qualification authorizes only internal synthetic CEREBRUM-DEV-004 development. It does not authorize public/protected scoring, real-institution claims, source-grounding claims, autonomous authority, or production use.