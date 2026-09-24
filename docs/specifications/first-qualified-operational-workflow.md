# First Qualified Operational Workflow

Status: `CANONICAL_SPECIFICATION_V1_NOT_SELECTED`

The First Qualified Operational Workflow (FQOW) is the first bounded customer
workflow used to implement and validate the complete platform path. It does not
permanently define Cerebrum's industry.

Machine-readable contract:
`schemas/workflows/qualification.schema.json`.

## Selection criteria

Choose the workflow with the strongest combination of:

1. painful and frequent operational disruption;
2. an accountable customer owner;
3. accessible historical or read-only data;
4. a measurable existing baseline;
5. a safe shadow-mode starting point;
6. explicit authority and escalation rules;
7. available domain experts;
8. a path from recommendation to approved operation;
9. meaningful economic or public value; and
10. reuse across later institutions or sites.

Logistics is a tie-breaker when opportunities are otherwise equal. A stronger
manufacturing, healthcare-operations, data-center, energy, retail,
construction, or other partner may be selected instead. Healthcare begins with
operational coordination and minimizes protected data; it does not begin with
autonomous diagnosis, treatment, medication, or patient-priority decisions.

## Required vertical slice

```text
Operational disruption
→ normalized observation
→ state and commitment update
→ assessment and alternative plans
→ action proposal
→ Kernel decision
→ human approval when required
→ Kernel reevaluation
→ governed execution or shadow comparison
→ outcome verification
→ state update
→ audit and reviewed experience
```

## Qualification progression

1. **Compile:** represent the workflow, objectives, resources, authority,
   policies, connectors, and measures in Institutional IR and a domain pack.
2. **Replay:** evaluate 30--100 historical disruptions without influencing
   operations.
3. **Shadow:** process live events and produce non-binding recommendations.
4. **Assisted operation:** allow exact, human-approved, Kernel-authorized
   actions through Execution Assurance.
5. **Qualified expansion:** add workflows, sites, and permissions only after
   predefined gates pass.

## Required measurements

- operational value: recovery time, downtime, throughput, delay, cost, and
  protected commitments;
- human burden: investigation, planning, review, correction, and approval time;
- decision quality: correctness, usefulness, acceptance, correction, and
  unnecessary abstention;
- safety: unsafe proposals, Kernel denials/overrides, and unauthorized committed
  actions;
- deployment reuse: engineering effort, configuration, expert review, and time
  required for the next site.

## Claim boundary

Qualification supports only the registered workflow, institution, data access,
domain pack, release, and operating mode. Replay is not a live pilot; shadow
recommendations are not executed value; projected savings are not realized
savings; and one qualified workflow does not establish horizontal production
readiness.