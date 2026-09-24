# Cerebrum System

Status: `INTERNAL_REFERENCE_ARCHITECTURE_NOT_PRODUCTION_AUTHORIZED`

Cerebrum is EDON's institutional-intelligence platform. The controlling target
is frozen in `CEREBRUM-PLATFORM-VISION-002`; C1 is one possible learned-model
layer inside its model-neutral Reasoning Runtime. The diagram below records the
older bounded reference composition currently represented in code. It is not
the complete target platform.

```text
Humans: goals, policy, reserved authority
                    |
Institution sources -> Institution Compiler -> Institutional IR
                    |                           |
                    v                           v
       Institution Gateway -> Deterministic State Engine
                                          |
                                 World Model + Memory
                                          |
       +------------------+---------------+------------------+
       |                  |                                  |
       v                  v                                  v
      C1          Planning + OR/solvers          Coordination/Prediction
       +------------------+---------------+------------------+
                                          |
                              non-binding proposed actions
                                          |
                                          v
                                       Kernel
                                          |
                               exact authorized action
                                          |
                                          v
                             Institutional environment
                                          |
                           outcomes + state changes
                              |                    |
                              v                    v
                         State Engine          ActionNet
                                                   |
                           qualification -> training release -> frozen C1
```

## Component responsibilities

| Component | Responsibility | Authority |
| --- | --- | --- |
| C1 | learned institutional interpretation, prediction, planning support, uncertainty, and proposals | none |
| Institution Compiler | sources to reviewable candidate Institutional IR | none |
| State Engine | deterministic, time-gated, separated state projection | no execution authority |
| World Model | current typed institutional state and uncertainty | descriptive |
| Memory | working, commitment, episodic, and retained institutional context | governed reads/writes |
| Planning | goals, decompositions, dependencies, contingencies, and replans | proposal only |
| OR/solvers | validated scheduling, allocation, routing, and capacity candidates | proposal only |
| Coordination intelligence | explicit and state-mediated multi-actor reasoning | hypothesis only |
| Institutional resilience analysis | anomaly, cascade, compromised-state, degraded-operation, containment, and recovery analysis | hypothesis and proposal only |
| Causal/provenance | horizontal lineage from source through outcome and experience | evidentiary |
| ActionNet | local capture, governed global qualification, and offline releases | training release only |
| Kernel | current reference policy, exact-request authorization token, and world-commit boundary; target role is authorization decisions only | reserved authorization boundary |
| Execution Assurance | target revalidation, reservation, dispatch, acknowledgement, reconciliation, and compensation | not implemented as a separate service |
| Evaluation and Release Registry | target signed artifact, evaluation, capability, limitation, and rollback custody | evidence only; not implemented as the complete target service |
| Deployment Controller | target compatibility, approval, scope, canary, attestation, containment, and rollback enforcement | not implemented |

## Architectural invariants

1. C1 output is always non-binding.
2. Epistemic, authority, execution, and outcome state remain distinguishable
   and cannot silently overwrite one another. The existing five-view state
   projector remains a compatibility predecessor.
3. Planning and optimization are separate interfaces with independently
   validated outputs.
4. Causal/provenance records touch every component but do not claim causality
   beyond their recorded evidence status.
5. ActionNet experience cannot update a runtime directly. Local review,
   de-identified rights-bound promotion, an offline release, a new model
   identity, protected evaluation, signed registry custody, deployment approval,
   runtime attestation, and controlled installation are required.
6. A new institution should not require institution-specific weight updates;
   it may still require compilation, retrieval, configuration, tools, and
   governed in-context adaptation.
7. Kernel authorization remains external to the Reasoning Runtime and cannot be
   generated or broadened by a model. Execution Assurance may act only on an
   unchanged, current, exact authorization.
8. A resilience hypothesis cannot directly isolate a system, deny a resource,
   change a configuration, or trigger another binding containment action.
9. Failure or compromise of C1 must leave a documented deterministic or manual
   degraded mode rather than silently widening model authority.

State paths are arrays in assertions and collision-safe JSON Pointers in
projected views. Same-class assertions with different values at the same latest
availability time are surfaced as conflicts rather than silently reconciled.

## Implemented reference upgrade

The repository now includes:

- `C1OperationsAdapter`, preserving the historical proposal firewall;
- new `EDON_C1_*` runtime configuration with historical environment-variable
  aliases;
- `InstitutionalStateEngine`, which projects the five separated state classes
  under a decision clock;
- `CausalProvenanceGraph`, an append-only evidence-status graph;
- `CerebrumSystem`, which combines state projection, C1 proposal generation,
  and provenance without requesting authorization or executing an action; and
- public JSON contracts for state assertions, projections, C1 model manifests,
  system cycles, and causal/provenance graphs.

These are bounded internal reference components, not a learned C1 result or a
production institutional control system.

## Target migration boundary

Future work adds the Institutional Control Graph; identity/capability, mandate,
commitment, reservation, receipt, and compensation services; the public v1
institutional-task API; Execution Assurance; unified audit stream; Release
Registry; Deployment Controller; runtime monitoring; domain packs; and the
First Qualified Operational Workflow. Existing experiments, schemas, `/api/*`
routes, C1 identities, and Kernel-token records remain unchanged until explicit
versioned migrations are implemented and tested.