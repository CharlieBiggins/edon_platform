# Executor and Kernel integration — design boundary, not a deployed system

Proposed product flow:

1. Preserve authenticated/permissioned observations and their availability times.
2. Compile institutional rules and observations into typed inputs with provenance.
3. C1 proposes a typed operational program. The proposal cannot create authority.
4. A deterministic executor checks types/references and computes prospective state.
5. Policy/Kernel checks request identity, jurisdiction, authorization, preconditions,
   resources, freshness and permitted state transitions against trusted records.
6. Only an authorized commit changes system state. Its certificate comes from
   that checked transition; contradictory model prose cannot override it.
7. Observe actual outcomes separately from predictions, reconcile discrepancies,
   and replan or terminate safely.

Determinism is not truth: incorrect source data, incomplete rules, erroneous
compilation or a flawed executor can still produce an incorrect result.
Reference IR and oracle certificates belong to evaluation, never to production
inference. The oracle-assisted inherited scorer is not the runtime Kernel.

Before a shadow pilot, test malformed/duplicate identifiers, invalid types,
authority-field injection, replayed/stale authorization, query-time boundaries,
equal-time tie-breaking, resource contention, delayed/missing/conflicting evidence,
executor/Kernel disagreement, rejected proposals, interrupted commits, idempotency,
monitoring failures, manual intervention and safe termination. Include an
engine-only baseline where structured inputs already determine the answer.

Model-only, tool-assisted and complete-system results must remain distinguishable.
Fair alternatives receive equivalent relevant tools and evidence. A reference
verifier preventing an unsafe output from being accepted does not make the raw
model safe. Certificates establish only what the checked rules/inputs warrant.

This document specifies future engineering work. No live authorization, customer
integration, executor changes or closed-loop training were implemented by the
comparison framework build.