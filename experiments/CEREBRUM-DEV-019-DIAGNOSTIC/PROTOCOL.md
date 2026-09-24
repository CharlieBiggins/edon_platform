# Protocol

## Purpose

DEV-018 demonstrated stable model acceptance near 82 percent and successful
deterministic containment, but it did not determine where the model's reasoning
first diverged. DEV-019 tests parsing, ordering, state execution, decision, and
certificate faithfulness through cumulative gold interventions.

## Repeated-measures design

The 32 fresh scenarios comprise both trajectories from 16 counterfactual
pairs: 12 pivotal, two invariant, and two contextual pairs. Each of the five
conditions uses the same packet schema and target. Only the availability of
oracle-verified support changes.

The primary endpoint is within-scenario exact-certificate recovery. Secondary
endpoints include decision recovery, semantic-state recovery, unsafe
authorization, intervention degradation, mechanism-specific behavior, and
Wilson intervals by condition.

## Interpretation

- Recovery with typed events implicates parsing or event normalization.
- Recovery with canonical order implicates temporal ordering.
- Recovery with predecision state implicates state execution.
- Recovery with the decision implicates decision selection or faithfulness.
- Failure after a gold decision implicates certificate generation or a
  multistage interaction.

These are cumulative interventions. The result must be described as the
earliest demonstrated recovery stage under this instrument, not as unique
causal identification.

## Boundaries

There is no training, checkpoint selection, or confirmation set. DEV-018 cases
are not reused. The result can inform the future temporal IR and DSL design but
cannot authorize transfer, deployment, authority, or IGI.