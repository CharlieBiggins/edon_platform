# Data design

## Layered model

ActionNet-008 separates reusable institutional mechanics from domain-specific claims:

```text
typed mechanism core
  -> domain pack
  -> jurisdiction pack
  -> institution pack
  -> workflow and renderer
  -> governed candidate
  -> expert review and adjudication
  -> frozen approved dataset
```

The mechanism core represents authority, evidence, policy, time, workflow, resources, routing, jurisdiction, conflict, consent, quorum, custody, obligations, budgets, quality holds, and recalls. A domain pack selects relevant workflows, evidence types, mechanisms, risk tier, jurisdictions, and expert specialties. Institution-specific policy is not inferred from the domain name and must arrive through an authorized institution pack.

## Candidate classes

1. `synthetic`: project-authored mechanism probes such as those in this package.
2. `source_compiled`: cases reconstructed from permissioned policies, standards, or protocols.
3. `expert_authored`: cases created by a verified domain expert with evidence references.
4. `institution_feedback`: governed corrections, overrides, appeals, incidents, and confirmed outcomes from the application.

None of these origins alone makes a label authoritative.

## Production feedback path

```text
app.edoncore.com
  -> governed feedback event
  -> privacy and tenant-permission filter
  -> ActionNet candidate construction
  -> deterministic expert routing
  -> independent review
  -> adjudication when required
  -> duplicate and protected-set checks
  -> dataset freeze
  -> release approval
  -> future Cerebrum development identity
```

Clicks, dwell time, unexplained acceptance, model self-output, raw sensitive payloads, unresolved disputes, and protected evaluation cases never become direct labels.

## Candidate state

All generated candidates in this package carry:

- `source_grounded=false`
- `expert_review_status=PENDING`
- `privacy_review_status=PENDING`
- `adjudication_status=PENDING`
- `training_eligible=false`
- `binding_authority=false`

Future processes must create new immutable review and dataset records rather than editing the frozen synthetic candidate in place.