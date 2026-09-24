# Cerebrum System component boundaries

| Component | Implemented reference | Remaining work |
| --- | --- | --- |
| C1 provider | deterministic and optional local Qwen providers | trained, protected-evaluated C1 release |
| State Engine | deterministic five-view time-gated projector | persistent distributed projector and connector reconciliation |
| World/memory | event-sourced world and governed episodic memory | production storage, semantic indexes, identity integration |
| Planning | typed goals, dependencies, plans, monitoring, replanning | evaluated learned long-horizon planner |
| Optimization | validated capacity-allocation adapter | production OR solvers and broader problem classes |
| Coordination | protected latent-coordination protocol shell | detector, instrument, forecasts, result |
| Institutional resilience | architecture, threat model, authority boundary, and staged evidence plan | protected range, detector, red-team replication, shadow evidence, authorized pilot |
| Causal/provenance | append-only typed graph and evidence status | durable graph store and independently validated causal methods |
| ActionNet | local governed experience, global promotion, offline releases | source-grounded contributions and protected external validation |
| Kernel | exact-request token and commit reference | production policy, distributed authority, external audit |

No component except the institution-local Kernel may authorize a binding
transition.