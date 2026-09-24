# System overview

Controlling vision: `CEREBRUM-PLATFORM-VISION-002`  
Status: `FROZEN_CONTROLLING_VISION_NOT_IMPLEMENTED`

EDON separates institutional knowledge, governed state, reasoning, authority,
execution, integration, experience, release, and deployment.

```text
Humans / applications
        |
Command Center / Cards / APIs
        |
Institutional Control Graph
        |
Reasoning Runtime -> Exact Action Proposal
        |
Delegated Authority and Commitment Layer
        |
Independent Kernel -> Decision Receipt
        |
Execution Assurance + Recovery -> Execution Receipt
                                            |
                           Observation + Connector Gateway
                                            |
                         systems / agents / robots / people
                                            |
                                outcomes + audit events
                                            |
                  Reviewed ActionNet -> Release Registry
                                            |
                                  Deployment Controller
                                            |
                                  Reasoning Runtime
```

Human approval is evidence returned through the Control Plane for Kernel
reevaluation. Evaluation evidence is returned through the Release Registry for
Deployment Controller review. Neither approval nor evaluation bypasses its
independent control boundary.

The Control Graph projects immutable evidence and service-owned lifecycle
records. Identity/capability, mandate, commitment, reservation, receipt, and
compensation services manage their records; the graph makes those records and
their consequences available for reasoning, authorization, audit, and replay.

## Control planes

1. **Knowledge plane:** source acquisition, extraction, reconciliation, review,
   provenance, and IR versioning.
2. **Control-graph plane:** versioned actors, systems, evidence, state,
   objectives, policies, mandates, commitments, resources, plans, actions,
   receipts, and outcomes under effective, recorded, and availability clocks.
3. **Experience plane:** ActionNet generation, capture, counterfactuals,
   qualification, training releases, and dataset lineage.
4. **Reasoning plane:** model and solver routing, assessment, simulation,
   calibration, abstention, proposals, and transfer inside the Reasoning Runtime.
5. **Continuity plane:** event-sourced world state, governed episodic memory,
   commitment tracking, observation lineage, and replay.
6. **Operations plane:** goals, plans, resources, agents, monitoring,
   correction, and review-gated learning candidates.
7. **Optimization plane:** validated scheduling, allocation, routing, and
   capacity candidates kept distinct from learned planning.
8. **Integration plane:** the Observation and Connector Gateway's tenant-bound
   evidence, system, resource, action-delivery, receipt, and outcome boundaries.
9. **Delegated-authority plane:** identity, capability, mandate, commitment,
   resource reservation, decision receipt, and compensation lifecycles.
10. **Authority plane:** independent Kernel checks over exact, version-bound
    proposals, graph state, mandates, commitments, resources, and evidence.
11. **Execution plane:** authorization revalidation, reservation, dispatch,
    acknowledgement, reconciliation, cancellation, compensation, and audit.
12. **Release plane:** protected evaluation, signed release custody, deployment
    approval, canaries, runtime attestation, monitoring, containment, and rollback.
13. **Resilience plane:** cross-system anomaly, cascade, coordination,
    containment, degraded-operation, and recovery hypotheses spanning the
    other planes. Its outputs remain non-binding and require Kernel policy.

The causal/provenance service is horizontal: it records what informed each
state assertion, C1 inference, plan, optimization candidate, authorization,
commit, outcome, and experience record. Recorded lineage is not automatically
a validated causal conclusion.

No result in the reasoning, integration, experience, or evaluation plane
directly authorizes an execution or deployment change. Events are evidence,
not permission. Execution Assurance consumes only exact Kernel decisions, and
the Deployment Controller consumes only signed compatible release evidence and
explicit deployment approval.

The proposed resilience plane treats all external evidence and analytical
components as potentially delayed, incomplete, compromised, or unavailable. It
must preserve source diversity, uncertainty, blast-radius limits, human-reserved
authority, degraded operation, and recovery. See
`docs/architecture/institutional-resilience.md`.

## Evidence maturity

`DESIGN -> READY -> DEVELOPMENT -> FROZEN_INTERNAL -> PROTECTED -> EXTERNAL -> PRODUCTION`

Advancement is per claim, not per repository or model name.

## Current implementation boundary

The existing repository implements bounded pieces of these planes, including a
C1 compatibility adapter, five-view state projector, world/event infrastructure,
Kernel exact-request tokens, transactional outbox, ActionNet governance, and
shadow-only gateways. It does not yet implement the complete Institutional
Control Graph, mandate/commitment/reservation services, receipt services,
Compensation Manager, Execution Assurance service, Deployment Controller,
public v1 API, production Command Center, or a qualified workflow.