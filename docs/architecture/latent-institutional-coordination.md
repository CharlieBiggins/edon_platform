# Latent institutional coordination

Status: `ARCHITECTURE_AND_RESEARCH_PROTOCOL_DEFINED_CAPABILITY_NOT_ESTABLISHED`

Latent institutional coordination occurs when multiple agents become causally
coupled through shared institutional state even though no direct message or
handoff connects them. Examples include agents reacting to queues, artifacts,
database mutations, resource allocations, schedules, or configuration changes
created by other agents.

```text
Agent A changes a queue
        |
        v
Agent B selects new work
        |
        v
Agent C reallocates a resource
        |
        v
Agent D modifies an artifact
        |
        v
collective outcome emerges without a direct communication chain
```

Message monitoring sees isolated actions. EDON's proposed coordination layer
instead analyzes the institutional state-transition graph.

## Cerebrum System coordination state

The coordination state is a time-gated projection of the institutional world.
It explicitly separates:

- agent-to-agent communication;
- agent actions;
- persistent artifacts and their lineage;
- database and other state mutations;
- resource changes and flows;
- queue and scheduling changes;
- code and configuration changes;
- direct and indirect causal dependencies; and
- candidate collective outcomes.

Every edge records occurrence time and the time it became available to the
controller. A prospective detector cannot use a future mutation, receipt, or
outcome to explain an earlier decision.

The machine-readable input contract is
`schemas/cerebrum/coordination-state.schema.json`.

## C1 reasoning pipeline

```text
detect -> attribute -> reconstruct -> predict -> govern
```

1. **Detect:** decide whether observed behavior is independent, directly
   coordinated, indirectly state-mediated, ambiguous, or insufficiently
   evidenced.
2. **Attribute:** identify participating agents, systems, resources, and
   artifacts without assuming that correlation proves coordination.
3. **Reconstruct:** return the evidence-grounded causal path connecting actions
   through institutional state.
4. **Predict:** estimate bounded downstream state changes and collective
   outcomes with calibrated uncertainty.
5. **Govern:** emit a non-binding risk hypothesis and recommended policy
   disposition for deterministic evaluation.

The output contract is
`schemas/cerebrum/coordination-hypothesis.schema.json`.

## Causal standard

The detector must distinguish at least four propositions:

- the agents' behavior is statistically associated;
- their actions share an institutional dependency;
- one action causally changes the state observed by another agent; and
- the resulting multi-agent behavior is directed toward a common outcome.

Only the latter two support a state-mediated coordination hypothesis. A shared
clock, common external shock, or coincidental use of the same resource must not
be labeled coordination without a supported path. Competing explanations and
missing edges remain explicit.

Controlled counterfactual pairs are central to evaluation. One pair may hold
all messages constant while changing the queue, artifact, or resource edge;
another may hold state constant while changing an explicit message. The label
must follow the causal intervention rather than vocabulary, agent identity, or
event volume.

## Safety and Kernel boundary

C1 never intervenes directly. Its coordination hypothesis has
`binding_authority=false` and `executed=false`. It may recommend monitoring,
requesting evidence, escalation, or evaluation of a candidate pause or denial.

The deterministic Kernel may act only under a separately approved policy that
specifies:

- the covered action or mutation type;
- the minimum evidence and confidence requirements;
- state-version and authorization preconditions;
- whether human review is mandatory;
- expiry, rollback, and appeal behavior; and
- an exact-request execution token.

The model cannot create a token, broaden the covered action, or convert its
risk prediction into authority.

## Current implementation map

The Cerebrum System already stores several required signals: message custody, world events,
agents, resources, plans, dependency-aware queues, assignments, outcomes,
model lineage, and transactional outbox lineage. The Institutional Environment
Gateway defines the umbrella observation path.

The following are not implemented:

- a unified coordination-state projector over all signal classes;
- typed persistent-artifact and code/configuration lineage adapters;
- a learned latent-coordination detector;
- causal-path attribution or emergent-objective inference;
- downstream collective-behavior forecasting;
- a validated deterministic coordination-risk policy for the Kernel; and
- protected unseen-institution evaluation or real-institution validation.

`CEREBRUM-LATENT-COORD-001` reserves the first research protocol. Its shell is
infrastructure only and contains no protected instrument or model result.

Latent coordination is one threat class within the broader institutional
resilience direction. Detection does not establish hostile intent, justify
containment, or authorize an action. See
`docs/architecture/institutional-resilience.md`.