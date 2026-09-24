# Institutional Control Graph

Status: `CANONICAL_SPECIFICATION_V1_NOT_IMPLEMENTED`
Vision: `CEREBRUM-PLATFORM-VISION-002`

The Institutional Control Graph is the Control Plane's versioned computational
representation of the institution. It answers what exists, what is happening,
how entities are related, what evidence supports the state, and which
objectives, policies, mandates, commitments, resources, proposals, actions, and
outcomes are affected.

Machine-readable contracts:

- `schemas/control-graph/node.schema.json`;
- `schemas/control-graph/edge.schema.json`; and
- `schemas/control-graph/snapshot.schema.json`.

## Custody model

The graph is a projection over immutable events and service-owned lifecycle
records. It is not an unrestricted write surface and does not replace the
authoritative systems from which evidence originates. Each graph version binds:

- tenant, institution, decision time, and controller-availability time;
- prior graph version and applied event range;
- Institutional IR, domain-pack, policy, and authority versions;
- node and edge content hashes;
- conflicts, compartments, provenance, and integrity status.

Corrections append evidence and produce a new version. Historical versions
remain replayable for decision reconstruction.

## Canonical node classes

- actor, organization, role, jurisdiction, system, facility, and connector;
- resource, capability, credential, reservation, and constraint;
- observation, evidence, state assertion, conflict, and incident;
- objective, policy, prohibition, exception, mandate, and approval;
- commitment, dependency, plan, proposal, action, and compensation;
- decision receipt, execution receipt, outcome, release, and deployment.

## Canonical relationship classes

Relationships are typed, directional, versioned, and evidence linked. Examples
include `MEMBER_OF`, `HAS_ROLE`, `CAN_PERFORM`, `DELEGATED_BY`, `AUTHORIZED_FOR`,
`OWNS`, `DEPENDS_ON`, `RESERVES`, `CONSTRAINS`, `AFFECTS`, `SUPPORTED_BY`,
`DISPUTES`, `PROPOSES`, `AUTHORIZES`, `EXECUTES`, `COMPENSATES`, and
`PRODUCES_OUTCOME`.

## Service ownership

A graph node does not manage its own lifecycle. The responsible service creates
and validates lifecycle records, and the graph represents them:

| Record | Owning service |
| --- | --- |
| identity and capability | Identity and Capability Registry |
| mandate and delegation | Mandate Service |
| commitment | Commitment Ledger |
| reservation | Resource Reservation System |
| decision receipt | Kernel/Decision Receipt Service |
| execution receipt | Execution Assurance |
| compensation record | Compensation Manager plus Kernel authorization |

## Query boundary

The Control Graph supplies the state used for assessment, planning, mandate
resolution, Kernel checks, audit, and human review. Queries are tenant and
compartment scoped and include graph version, effective time, evidence lineage,
conflict status, and uncertainty. A graph query cannot grant authority.

## Invariants

1. No graph write silently changes policy, authority, commitment, reservation,
   execution, or outcome state outside its owning lifecycle service.
2. Capability edges never imply mandate or authorization.
3. Inferred relationships carry derivation lineage and uncertainty.
4. Conflicts and disputed evidence remain explicit.
5. A decision binds the exact graph version used by the Kernel.
6. Historical graph versions and their evidence remain reconstructable.
7. Graph compromise or unavailability triggers a registered degraded mode; it
   never widens authority.