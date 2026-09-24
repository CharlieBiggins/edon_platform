# Cerebrum/C1 terminology migration

Effective for architecture documents dated 2026-08-30:

> C1 is the architectural name for the learned component historically referred
> to as Cerebrum in EDON experimental literature. Historical experiment
> identities, results, artifacts, and claims retain their original terminology.

## Mapping

| Historical term | Current architectural term |
| --- | --- |
| Cerebrum model | C1 learned-model layer |
| Cerebrum provider | C1 provider, with historical API alias preserved |
| Cerebrum adapter | C1 proposal adapter, using the unchanged authority firewall |
| Cerebrum | Cerebrum System when referring to the complete architecture |

This is a terminology and system-boundary migration, not a scientific result,
model release, weight conversion, or reclassification of prior evidence.

## Compatibility

- Historical experiment IDs beginning with `CEREBRUM-` do not change.
- Historical manifests and frozen results are not rewritten.
- Existing `OperationsProposalAdapter` and `EDON_CEREBRUM_*` integrations remain
  supported.
- New code may use `C1OperationsAdapter` and `EDON_C1_*`.
- API status retains historical `provider` and `model_lineage` fields while
  adding an explicit nested `c1` component record.