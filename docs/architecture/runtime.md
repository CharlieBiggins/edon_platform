# Governed runtime

`CEREBRUM-PLATFORM-VISION-001` separates this older combined runtime into the
Reasoning Runtime, independent Kernel, Execution Assurance, Evaluation and
Release Registry, Deployment Controller, and runtime monitoring. The current
implementation remains an internal reference and is not reclassified by the
new names.

The runtime turns non-authoritative proposals into auditable institutional
actions only after deterministic checks.

```text
Cerebrum proposal
      -> schema validation
      -> policy and authority checks
      -> resource/workflow checks
      -> human approval when required
      -> signed deterministic commit
      -> immutable audit record
```

The runtime must support fail-closed behavior, replay protection, version pinning,
revocation, rollback, provenance capture, and separation of duties.

## Implemented internal runtime

The current deterministic runtime validates that mechanisms are approved,
non-binding, source-linked, internally consistent, and conflict-resolved. It
evaluates typed facts, returns `ALLOW`, `DENY`, or `ABSTAIN` certificates, and
executes `SET`/`DELETE` event queues in canonical sequence, priority, and ID
order. Every result includes input or final-state hashes and an execution trace.

The review registry provides versioned promotion, rollback, distinct-reviewer
requirements, and a SHA-256-linked audit chain. The internal Kernel reference
now adds expiring exact-mutation HMAC tokens, authority and world-version
binding, authenticated-actor binding, and an immutable replay ledger. World
commits atomically create lease-deliverable outbox messages.

The hierarchy reference adds immutable global/domain/region/facility/edge
scopes, redacted version-bound state projection, least-common-ancestor routing,
additive escalation history, and a validated non-binding optimization-provider
boundary. Global or regional candidates still require a local Kernel decision.

This remains a local symmetric-key reference. It is not a legal signature
service, hardware-backed key system, distributed authorization quorum, or
external production commit authority.