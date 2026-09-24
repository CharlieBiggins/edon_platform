# Kernel tokens, transactional outbox, and shadow supervision

This document describes the current internal secure-commit reference. In the
target platform, Kernel issues authorization decisions and a separate Execution
Assurance service revalidates, reserves, dispatches, reconciles, and compensates.
The existing token/outbox path remains a compatibility predecessor until that
separation is implemented and tested.

EDON's internal secure-commit reference separates three responsibilities:

```text
Cerebrum proposal
    -> typed operations adapter
    -> immutable shadow cycle
    -> independent Kernel authorization
    -> exact-request execution token
    -> version-bound world commit
    -> transactional outbox
    -> downstream delivery and recovery
```

## Exact-request Kernel tokens

The local Kernel authority issues expiring HMAC-SHA256 tokens bound to tenant,
world, authenticated actor, authority version, expected world version, event
identity, event type, and the canonical mutation hash. Successful consumption
is stored in an immutable SQLite replay ledger. Idempotent retry of the same
event is permitted; use for a different request is rejected.

`KERNEL_AUTHORIZER` and `KERNEL_COMMITTER` are separate API roles. The secure
world endpoints accept the exact token rather than an arbitrary authorization
reference.

This is symmetric local signing, not a production public-key infrastructure,
hardware security module, legal signature, distributed authorization quorum,
or external identity-provider integration.

## Transactional outbox

Every world event creates a `world.events` outbox message in the same SQLite
transaction as its event, snapshot, and materialized state update. Workers use
bounded leases, immutable delivery-audit records, acknowledgements, retries,
lease-expiry recovery, and terminal dead status after a configured attempt
limit. The authorization token itself is not copied into the message; only its
hash is retained.

## Cerebrum operations adapter

The adapter accepts only `ABSTAIN`, `CREATE_GOAL`, `CREATE_PLAN`,
`DISPATCH_STEP`, `REPLAN`, and `CANCEL_STEP` proposals. It rejects authorization
references, execution tokens, signatures, commit flags, or any claim of binding
authority. Every accepted proposal is bound to its input and model lineage by
content hashes.

The deterministic provider remains the default. `CEREBRUM-BUILD-001` adds an
explicitly enabled local Qwen/LoRA provider behind the same adapter. It parses
one JSON object, fails closed to `ABSTAIN` on malformed or unavailable output,
hard-rejects authority-bearing output, and requires a registered model lineage.
This does not widen the proposal or authority surface.

## Shadow supervisor

The supervisor constructs a version-pinned context from current operations,
alerts, ready steps, and deterministic assignment proposals. It records the
Cerebrum proposal in an immutable shadow-cycle database and never mutates the
world. Promotion from shadow recommendation to execution requires a separately
issued Kernel token.

## EDON-OPS-002

The internal integration evaluation passes ten gates covering proposal/commit
separation, capability matching, atomic resources, expected-outcome evidence,
replanning, learning eligibility, history preservation, replay, outbox delivery,
and token request binding. This is deterministic internal integration evidence,
not learned autonomy or external validation.

## Containment and degraded operation

An anomaly, cascade, coordination, poisoning, or compromise hypothesis is
evidence for review, not authority to intervene. A containment or recovery
action must identify its target, permitted mutation, expected state version,
expiry, blast radius, rollback or compensating action, required reviewers, and
the evidence threshold registered by policy.

High-impact actions such as service isolation, configuration rollback, resource
denial, shutdown, or emergency reallocation must fail closed to the applicable
human or multi-party review. If C1 or Cerebrum is unavailable or suspected to be
compromised, Kernel must not expand its authority; the institution instead
enters a separately documented deterministic or manual degraded mode.