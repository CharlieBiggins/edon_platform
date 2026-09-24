# ActionNet Experience and Learning Contract

Status: `CANONICAL_SPECIFICATION_V1_NOT_IMPLEMENTED`
Specification: `CEREBRUM-MATURE-PLATFORM-SPEC-001`

This contract governs how operational evidence becomes reviewed institutional
experience and, conditionally, training or evaluation material. It composes the
existing ActionNet custody, review, abstraction, counterfactual, coverage, and
release schemas rather than replacing them.

Machine-readable mature binding:
`schemas/actionnet/mature-experience-learning-contract.schema.json`.

## Required distinctions

Every trajectory keeps separate:

- direct observations and source-system reports;
- perception or model-generated interpretations;
- simulations, forecasts, and counterfactual alternatives;
- human judgments, corrections, appeals, and approvals;
- proposals and Kernel decisions;
- dispatch, acknowledgement, partial effect, and completion;
- outcome assessment and officially verified outcome;
- causal hypothesis and validated causal conclusion.

## Experience lifecycle

```text
Captured trajectory
→ source and receipt binding
→ rights, privacy, and retention review
→ domain and safety review
→ quality and contamination review
→ tenant-local eligibility
→ optional minimized abstraction
→ protected overlap review
→ frozen training or evaluation release
→ independent evaluation
→ signed model release
→ Deployment Controller review
```

Raw customer records do not automatically enter global training. Institution-
local memory remains context-only unless a separately reviewed permitted-use
record authorizes another use.

## Quality and provenance

The contract binds initial graph/state versions, observations, uncertainty,
plans considered, proposal, decision receipt, execution receipt, outcome
evidence, verification policy, correction history, counterfactual lineage,
review identities, rights, permitted uses, and content hashes.

## Learning and deployment separation

ActionNet can create an eligible frozen release. It cannot train online, change
production weights, install a model, expand a capability envelope, change
routing eligibility, or authorize execution. Training, evaluation, release
registration, and deployment are separate transactions.

## Invariants

1. Protected evaluation material is training-ineligible.
2. Simulation and counterfactual records cannot be labeled as observed outcomes.
3. A receipt proves custody, not correctness by itself.
4. Rights and privacy permission are explicit per permitted use.
5. Negative, failed, abstained, overridden, and compensated outcomes remain
   available for authorized review and cannot be silently filtered away.
6. Cross-institution abstractions exclude prohibited tenant information and
   retain source and review lineage.