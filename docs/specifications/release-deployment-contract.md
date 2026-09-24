# Release and Deployment Contract

Status: `CANONICAL_SPECIFICATION_V1_NOT_FULLY_IMPLEMENTED`

The Evaluation and Release Registry records qualified artifacts. A separate
Deployment Controller decides whether a signed release may enter a particular
runtime scope.

Machine-readable contracts:

- `schemas/releases/release-contract.schema.json`;
- `schemas/releases/deployment-approval.schema.json`; and
- `schemas/releases/runtime-attestation.schema.json`.

## Release binding

Every release binds:

- model, adapter, tokenizer, compiler, Institutional IR, and domain-pack hashes;
- connector and schema compatibility;
- evaluation instruments, predictions, scores, safety results, and limitations;
- qualified workflows and unsupported conditions;
- capability envelope and deployment scope;
- required human approvals;
- canary limits and monitoring thresholds;
- automatic containment rules;
- rollback target and incident-reconstruction artifacts.

A registry entry does not install the release and does not imply production
authorization.

## Deployment decision

Before installation, the Deployment Controller verifies signatures, artifact
hashes, compatibility, environment attestation, approved scope, approval
quorum, canary budget, monitoring configuration, containment behavior, and a
loadable rollback target. It records an immutable deployment decision.

## Runtime control

Runtime and Execution Assurance telemetry feed monitoring. Threshold violations
may freeze proposals, reduce scope, enter a deterministic/manual degraded mode,
or request rollback according to the signed containment policy. Monitoring
cannot silently install an unregistered replacement.

## Invariants

1. Passing evaluation does not automatically authorize deployment.
2. Deployment approval is specific to release, environment, workflow, tenant,
   domain pack, and capability envelope.
3. Canary expansion requires new evidence and approval under the contract.
4. Rollback preserves the failed release, telemetry, decisions, and audit trail.
5. Online operational experience does not update production weights directly.