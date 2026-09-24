# Institutional world state and episodic memory

EDON's first continuity layer stores institutional state outside model weights
and context windows. Cerebrum may estimate state and propose events, but only an
event carrying an explicit authorization reference may enter the durable world
log. This reference implementation records the reference; production systems
must cryptographically validate it against the institution-local Kernel.

## Event-sourced world state

Each tenant and world has an independent immutable event chain. Commits require
an expected version, which prevents stale planners or agents from silently
overwriting newer state. Every accepted event creates an immutable snapshot.

Supported reference mutations are `SET`, `DELETE`, `INCREMENT`,
`APPEND_UNIQUE`, `REMOVE`, and full-root restoration. Paths are arrays of keys,
not executable expressions. Parent objects must already exist, which makes
misspelled or structurally invalid mutations fail closed.

```text
Cerebrum proposal
    -> Kernel authorization
    -> version-bound world event
    -> immutable event and snapshot
    -> replay verification
```

Restoration appends a new event pointing to a preserved snapshot. It never
deletes or rewrites history.

## Episodic memory

Episodes remain tenant-isolated and include world identity, occurrence time,
sensitivity, source event identifiers, provenance, retention, and content hash.
Retrieval uses a deterministic lexical reference scorer so the current package
has no hidden embedding-model dependency. Production retrieval may add approved
indexes without changing access or provenance rules.

Sensitivity is explicit: `PUBLIC`, `INTERNAL`, `CONFIDENTIAL`, or `RESTRICTED`.
Callers must provide their permitted levels. Expired memories and tombstoned
records are excluded. Tombstones preserve the original custody record while
preventing ordinary retrieval.

## Current boundary

This is a bounded SQLite reference for internal prototypes. It is not a
production distributed database, identity provider, secrets manager, legal
record-retention system, or consensus implementation. It establishes the
contracts required before long-horizon planning and multi-agent coordination are
added.

The Institutional Environment Gateway may submit time-gated evidence about
agents, systems, resources, artifacts, and configuration state. Latent-
coordination analysis consumes a non-authoritative projection of this history;
ingestion and model inference do not authorize mutation of durable state.


The Institutional Environment Gateway may submit time-gated evidence about
agents, systems, and resources to this continuity layer. Ingestion alone does
not make an external report authoritative: durable world mutation still
requires explicit authorization, version checks, provenance, and conflict
preservation.