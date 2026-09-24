# Institutional IR Lifecycle

Status: `CANONICAL_SPECIFICATION_V1_NOT_FULLY_IMPLEMENTED`

Institutional IR represents policies, authority, objectives, commitments,
resources, capabilities, actions, evidence rules, and domain semantics. It is a
governed artifact with an explicit lifecycle rather than a mutable prompt.

Machine-readable contract:
`schemas/institution/ir-lifecycle.schema.json`.

## Lifecycle

```text
DRAFT
→ VALIDATED
→ IN_REVIEW
→ APPROVED
→ ACTIVE
→ AMENDED
→ SUPERSEDED
→ MIGRATING
→ RETIRED
```

Validation establishes schema and internal consistency only. Approval records
accountable human review. Activation is a separate, scoped deployment action.

## Required custody

Every IR version binds:

- source documents and extraction lineage;
- owner, jurisdiction, effective dates, and review status;
- compiler and schema versions;
- policy, authority, objective, connector, and domain-pack content hashes;
- review findings, approvals, dissent, and unresolved conflicts;
- compatibility and migration requirements;
- the treatment of active plans, authorizations, reservations, and executions
  when governance changes.

## Change handling

Material amendments create a new version. The Control Plane must identify
active decisions affected by an amendment and apply the registered transition
policy: continue, revalidate, pause, cancel, compensate, or escalate. A new IR
version cannot retroactively make an earlier action authorized.

## Invariants

1. Observed practice is not silently promoted to legitimate policy.
2. Compiler output remains a candidate until reviewed and approved.
3. Activation is scoped by institution, domain pack, workflow, and time.
4. Superseded versions remain available for replay and incident reconstruction.
5. Retiring IR does not delete the evidence used by historical decisions.