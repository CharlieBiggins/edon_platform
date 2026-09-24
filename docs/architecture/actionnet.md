# ActionNet

ActionNet generates, captures, and qualifies governed institutional experience:

- normal trajectories;
- pivotal counterfactual pairs;
- invariance pairs;
- contextually dominated pairs;
- multi-event queues;
- failures, delayed events, conflicts, and unsafe paths.

Every generated dataset requires a qualification report covering determinism,
observability, label isolation, split lineage, contradictions, duplicates,
unreachable states, renderer balance, oracle agreement, and safety coverage.

Synthetic success is not real-institution validity. Source-grounded generation
requires independently reviewed institutional twins and protected evaluation.

Candidate experience derived from the Institutional Environment Gateway may
link the information available before a decision, agent actions, artifact and
resource changes, causal dependencies, proposal and authorization lineage,
committed mutations, and observed outcomes. Operational capture alone never
makes a record authoritative or training eligible.

The lifecycle is capture -> review -> qualification -> content-bound training
release -> frozen C1 version. ActionNet does not perform binding execution and
cannot update C1 weights directly.

Each institution has a tenant-isolated local experience ledger. The governed
Global ActionNet layer accepts only normalized, de-identified, rights-bound
abstractions after local eligibility and overlap checks. It stores a source
commitment rather than raw tenant data and revalidates the local source before
freezing an offline training release.

Future development data for latent coordination must receive a new ActionNet
identity. The protected `CEREBRUM-LATENT-COORD-001` instrument cannot be reused
as training data.

## Implemented generator

`src/edon/actionnet/generator.py` now generates deterministic certificate,
transition, queue-trace, and pair-contrast cases from promoted IR. It creates
normal states, per-condition failures, missing-value edge cases, event
transitions, a canonical queue, and pivotal counterfactual pairs.

Public model inputs and oracle labels are held in separate payloads and receive
independent hashes. `src/edon/qualification/engine.py` checks leakage,
contradictory targets, reachability, task coverage, pivotality, and unsafe failure
allows before training orchestration is permitted.

## Complete preserved simulation worlds

The repository also contains the full executable ActionNet research lineage,
not only the platform generator:

| Package | Role | Materialized corpus | Controls |
| --- | --- | ---: | ---: |
| `ACTIONNET-DATA-QUAL-001` | Original paired-trajectory world | 720 examples | 29/29 |
| `ACTIONNET-DATA-QUAL-002` | Observable rendering repair | 720 examples | 33/33 |
| `ACTIONNET-DATA-QUAL-003` | Multi-view repair world | 3,600 train + 300 validation | 23/23 |
| `ACTIONNET-DATA-QUAL-004` | Independent EventNet queue world | 5,040 train + 420 validation | 31/31 |
| `ACTIONNET-DATA-QUAL-005` | Fresh structured-repair world | 5,040 train + 420 validation | 31/31 |
| `ACTIONNET-DATA-QUAL-006` | Appeal-boundary narrow-repair world | 8,064 train + 1,344 validation | 35/35 |

Each package under `experiments/` includes its generator, scheduler/oracle
implementation, generated JSONL corpus, lineage records, preregistration,
qualification report, checksums, and original tests. Versioned loaders live at
`src/edon/actionnet/eventnet/`; they preserve the dependency chain instead of
flattening the worlds into the smaller IR-driven MVP generator.

Regenerate and verify the full lineage in one command:

```bash
python scripts/data/rebuild_actionnet_world.py
```

Verify the already materialized corpora without rewriting them:

```bash
python scripts/data/rebuild_actionnet_world.py --verify-only
```

Reserved future-public and protected semantic families remain unmaterialized.
That is an intentional custody boundary in the registered design, not a missing
part of the internal simulation world. See the DATA-QUAL-005 preservation note
for its recorded historical source-manifest discrepancy. DATA-QUAL-006 adds
fresh institution lineages and balanced resolved/unresolved appeal timing; it
does not reuse or reinterpret the exposed DEV-004 validation cases.
