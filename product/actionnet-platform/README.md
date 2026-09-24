# ActionNet Platform

ActionNet is the reviewed experience and evaluation plane within the unified
Cerebrum platform. It does not itself authorize deployment or execution.

ActionNet Platform is EDON's governed institutional-experience product. Version
0.2 adds an active experience-construction layer beneath its product surfaces:

1. **Canonical Institutional IR:** one versioned grammar for actors, roles,
   authority, capabilities, resources, goals, obligations, policies, evidence,
   workflows, plans, dependencies, events, actions, outcomes, risks, conflicts,
   and temporal constraints. Every object maps into
   `I=(X,E,R,A,P,W,T,C,Sigma)`.
2. **Composition Engine:** validates registered Atlas edges, binds mechanisms to
   IR objects, orders causal dependencies, executes typed transitions, and
   records replay-verified horizon states.
3. **Counterfactual Engine:** actively forks stored executable trajectories,
   applies registered interventions, deterministically replays each branch, and
   creates governed child experiences.
4. **Temporal and Epistemic State:** makes seconds-to-months horizons and known,
   unknown, estimated, stale, contradictory, delayed, untrusted, and
   probabilistic state explicit.
5. **Human-Behavior Scenarios:** represents objectives, incentives, trust,
   fatigue, risk tolerance, information access, cooperation, strategic behavior,
   and bounded rationality as assumption-driven scenarios—not human ground truth.
6. **Governed Abstraction Intake:** accepts only locally minimized abstractions,
   records source rights and redaction attestations, rejects named raw-sensitive
   fields, and requires the normal privacy and release gates.

These engines extend the original six product surfaces:

1. **Atlas:** institutional mechanisms and evidence-graded composition edges.
2. **Experience Ledger:** causal, counterfactual, failure, and protected records.
3. **World Lab:** deterministic procedural and adversarial institution blueprints.
4. **Curriculum:** registered coverage snapshots and acquisition recommendations.
5. **Intervention Lab:** non-binding, constraint-bearing intervention candidates.
6. **Trust and Vault:** reviews, overlap custody, model exposure, audit, and releases.

All records default to non-authoritative and non-binding. Experiences default to
`training_eligible=false`; protected records cannot enter training releases.

## Local start

```bash
export EDON_API_KEYS='{
  "replace-author-token-0000":"ACTIONNET_AUTHOR",
  "replace-custodian-token-0":"ACTIONNET_CUSTODIAN",
  "replace-release-token-000":"ACTIONNET_RELEASE_MANAGER"
}'
PYTHONPATH=src python -m edon.cli serve --state-dir var/edon
```

Run the complete internal product evaluation:

```bash
PYTHONPATH=src python evaluations/ACTIONNET-PLATFORM-001/run_evaluation.py
```

Run both internal product evaluations:

```bash
PYTHONPATH=src python evaluations/ACTIONNET-PLATFORM-001/run_evaluation.py
PYTHONPATH=src python evaluations/ACTIONNET-PLATFORM-002/run_evaluation.py
```

## Status

`ACTIONNET-PLATFORM-002` is an internal active-experience MVP. Platform 001
passes 18/18 workflow gates and Platform 002 passes 26/26 active-experience
integration gates. It is not production ready until the controls in
`PRODUCTION_READINESS.md` are independently closed.
Frozen ActionNet research releases 001--008 remain immutable evidence sources;
the platform consumes or references them without rewriting their results.

The additive ActionNet Learning Network keeps each institution's full
experience tenant local. Only reviewed, de-identified, rights-bound abstractions
may enter Global ActionNet, and only an immutable offline release may be bound
to a future `C1-vN` record. See `product/actionnet-learning-network/`.

## Contribution experiment

`experiments/CEREBRUM-PLATFORM-CONTRIB-001/` contains the matched experiment
testing whether Platform 002 compositions and counterfactuals improve learning
over count-matched single-mechanism experience. Its transparent proxy shows a
strong internal signal; the registered two-seed Qwen execution remains blocked
until an external CUDA/model runtime is supplied.