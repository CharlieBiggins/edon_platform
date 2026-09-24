# Institutional resilience under AI-speed disruption

Status: `RESEARCH_DIRECTION_DEFINED_CAPABILITY_NOT_ESTABLISHED`

Policy context checked: 2026-08-30

This document defines a bounded security and continuity direction for EDON. It
does not claim that EDON can defeat artificial superintelligence, repel a state
adversary, protect national infrastructure, or operate within a national-security
environment.

## Bounded thesis

As capable AI increases the speed and complexity of both legitimate operations
and adversarial disruption, institutions may need machine-speed situational
awareness, causal reconstruction, coordination, containment proposals, and
recovery support while accountable humans retain binding authority.

Within that framing:

- C1 supplies non-binding learned interpretation, prediction, and planning
  support;
- the Cerebrum System models the institution and coordinates analytical
  components;
- the deterministic State Engine preserves distinct evidence and commitment
  classes;
- the Institutional Environment Gateway observes agents, systems, and
  resources;
- Kernel evaluates every proposed binding intervention under separately
  authorized policy; and
- ActionNet captures qualified exercises, incidents, outcomes, failures, and
  recoveries for later offline learning.

The relevant unit is the changing institution, not an individual model or
agent. The research question is whether EDON can detect and help contain unsafe
cross-system institutional dynamics that may remain invisible when each agent
or system is monitored independently.

## Relationship to cybersecurity

EDON is proposed as complementary to cybersecurity, safety engineering,
incident response, and mission assurance. It does not replace them.

| Existing control focus | Proposed EDON focus |
| --- | --- |
| identities, endpoints, networks, software, and data | typed institution-wide state and authority |
| confidentiality, integrity, and availability | objectives, commitments, queues, resources, dependencies, and consequences |
| alerts and system-local incidents | cross-system causal paths and institutional cascades |
| access control and technical policy | deterministic action-level institutional authorization |
| restoration of affected services | coordinated continuity, degraded operation, and recovery proposals |

The boundary is intentionally overlapping. A production deployment would rely
on established cybersecurity and operational controls rather than claiming a
new system makes them unnecessary.

## Threat model

The proposed research scope includes:

- **state poisoning:** false inventory, capacity, financial, clinical,
  scheduling, telemetry, or readiness evidence causes individually reasonable
  components to produce an unsafe collective result;
- **cross-system cascade:** one action changes queues, resources, artifacts, or
  configuration observed by downstream actors, causing rapid institutional
  amplification;
- **latent coordination:** compromised or misaligned actors coordinate through
  shared state rather than direct messages;
- **authority confusion:** an actor, connector, or model attempts to present a
  report, inference, recommendation, or delivery receipt as authorization;
- **temporal manipulation:** delayed, reordered, replayed, or future-leaking
  evidence changes a controller's apparent decision context;
- **resource exhaustion:** coordinated demand depletes staff, compute, money,
  inventory, transport, or other bounded capacity;
- **compromised analytical component:** one model, solver, adapter, or data
  source behaves adversarially or becomes unavailable; and
- **provenance suppression:** missing or altered lineage obscures the path from
  observation through decision, action, and outcome.

This architecture record does not cover strategic deterrence, offensive cyber
operations, weapons control, intelligence collection authority, or general ASI
containment. Those require separate legal, technical, policy, and safety
frameworks.

## Proposed resilience loop

```text
untrusted multi-source observations
              |
              v
time-gated separated institutional state
              |
              v
anomaly + cascade + coordination hypotheses
              |
              v
causal reconstruction + competing explanations
              |
              v
bounded forecast + uncertainty + affected objectives
              |
              v
non-binding containment / degradation / recovery proposal
              |
              v
Kernel policy + human-reserved authority
              |
              v
exact authorized action or BLOCK / REVIEW / ESCALATE
              |
              v
verified outcome -> State Engine + Local ActionNet
```

No stage before Kernel has binding authority. Detection does not itself justify
intervention, and recorded provenance does not automatically establish causal
attribution.

## Required safety invariants

1. A model, solver, connector, or detector cannot mint or broaden authority.
2. Reports, observations, inferences, authorizations, deliveries, and committed
   state remain distinguishable.
3. Decisions use only information available to the controller at the registered
   decision time.
4. High-impact conclusions require source diversity, explicit uncertainty, and
   competing-explanation records.
5. Response scope is least-privilege, version-bound, expiring, and limited to a
   registered blast radius.
6. High-risk containment, isolation, shutdown, or resource-denial actions
   require the applicable human or multi-party review.
7. The institution retains documented manual, degraded, and recovery modes when
   Cerebrum, C1, the gateway, or a dependency is unavailable.
8. Irreversible action is prohibited unless a separately approved policy and
   accountable authority explicitly permit it.
9. Operational incidents and memory writes cannot update C1 weights online.
10. Every authorized action must produce an auditable receipt and outcome or an
    explicit unresolved state.

## Evaluation program

A credible evidence program should advance through separately frozen stages:

1. **Definition:** preregister assets, actors, sources, authority, objectives,
   attack classes, baselines, information clocks, metrics, and exclusions.
2. **Synthetic institutional range:** test state poisoning, cross-system
   cascades, latent coordination, authority spoofing, resource exhaustion, and
   component outage under deterministic oracles where available.
3. **Digital-twin or cyber-range evaluation:** use independently constructed
   environments and matched information, model, compute, and response budgets.
4. **Independent red-team replication:** freeze controllers before protected
   attacks and score them under independent custody.
5. **Real-institution shadow study:** observe prospectively without delivering
   actions; compare against current operations and expert teams.
6. **Bounded action pilot:** only after legal authorization, external security
   review, rollback drills, explicit human escalation, and an independently
   approved Kernel policy.

Required metrics include detection precision and recall, false-intervention
rate, time to detection, time to safe stabilization, objective loss, unsafe
authorizations, causal-path accuracy, forecast calibration, degraded-mode
continuity, recovery completeness, and performance against matched baselines.

Success on a synthetic range would support only that registered range. It would
not establish national-infrastructure protection, general adversary resistance,
ASI defense, or production readiness.

## U.S. policy context

The following sources provide dated policy context rather than evidence for
EDON. Their inclusion is descriptive and does not imply endorsement,
government affiliation, procurement eligibility, authorization, or validation.

- The White House's June 5, 2026 fact sheet on AI in the national-security
  enterprise describes objectives including robust, steerable, controllable
  systems, multiple model vendors, and clear accountability under the chain of
  command: [AI in the National Security Enterprise](https://www.whitehouse.gov/fact-sheets/2026/06/fact-sheet-president-donald-j-trump-signs-historic-directive-on-ai-in-the-national-security-enterprise/).
- The White House's June 2, 2026 fact sheet describes AI-enabled cybersecurity
  and critical-infrastructure priorities: [Advanced AI Innovation and Security](https://www.whitehouse.gov/fact-sheets/2026/06/fact-sheet-president-donald-j-trump-promotes-advanced-artificial-intelligence-innovation-and-security/).
- The July 2025 *America's AI Action Plan* discusses critical-infrastructure
  cybersecurity, secure-by-design AI, adversarial inputs including data
  poisoning, and AI incident response: [America's AI Action Plan](https://www.whitehouse.gov/wp-content/uploads/2025/07/Americas-AI-Action-Plan.pdf).

Policy alignment is not scientific validation. EDON must satisfy its own frozen
evaluation, safety, privacy, authority, legal, and independent-replication gates.

## Current claim boundary

The repository currently provides component architecture, deterministic state
separation, provenance, Kernel controls, environment and agent gateway
contracts, ActionNet custody, operations references, and a latent-coordination
protocol shell. It does not provide a validated institutional-attack detector,
a causal attribution result, a protected resilience benchmark, an authorized
containment controller, a real critical-infrastructure result, or a
national-security capability.