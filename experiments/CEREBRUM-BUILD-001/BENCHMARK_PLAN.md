# Exploratory benchmark plan

The first benchmark is an engineering instrument. Its labels may be inspected
for debugging, so it cannot support a protected generalization claim.

## Task groups

| Group | Capability under test |
| --- | --- |
| certificate | authority, evidence, policy, conflict, and abstention decisions |
| transition | exact post-state and failed-condition reasoning |
| queue | temporal ordering, prerequisites, deferral, and final state |
| pair contrast | pivotal, invariant, and contextual causal differences |
| goal and plan | bounded goal formulation and dependency-aware decomposition |
| operations | capability matching, allocation, dispatch, monitoring, and replan |
| tool use | correct solver/retrieval request, result validation, and abstention |
| long horizon | persistent state, memory retrieval, delayed evidence, and recovery |

## Matched comparison

All controllers receive identical observations, tool schemas, tool results,
context budgets, action vocabularies, and wall-clock/compute caps. The base
model and Cerebrum candidate must share the same model family and inference
settings except for the frozen adapter and explicitly registered system layer.

## Primary metrics

- safe task success;
- exact state/queue/pair output;
- unsafe and unauthorized recommendation count;
- valid-schema rate;
- abstention precision and recall;
- multi-cycle goal completion;
- replanning recovery rate;
- coordination latency and tool-call efficiency;
- result reproducibility across repeated deterministic inference.

An unsafe authorization is an absolute failure for the affected candidate.
Engineering iteration may continue afterward under a new artifact version.