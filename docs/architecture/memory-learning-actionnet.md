# Memory, local experience, and governed learning

Status: `INTERNAL_REFERENCE_IMPLEMENTED_NOT_PRODUCTION_VALIDATED`

The controlling platform vision adds two mandatory boundaries after protected
evaluation: a signed Evaluation and Release Registry and a separate Deployment
Controller. No ActionNet release or C1 disposition directly changes runtime
traffic.

EDON separates immediate institution-specific adaptation from changes to model
weights.

```text
frozen C1 version
  -> institution IR + current world state + institution-local memory
  -> contextual reasoning without weight modification
  -> non-binding proposal
  -> Kernel decision and authorized execution
  -> state change, outcome, correction, failure, or recovery
  -> tenant-local ActionNet experience
  -> local review, privacy, lineage, safety, and overlap gates
  -> de-identified rights-bound Global ActionNet abstraction
  -> immutable offline training release + protected evaluation reservation
  -> offline training
  -> frozen C1-vNext record
  -> safety/performance/transfer disposition
  -> shadow eligibility, controlled deployment eligibility, or rollback record
```

## Distinct stores

| Store | Purpose | Weight-update effect |
| --- | --- | --- |
| Institutional memory | Current and historical facts for one tenant/world | none; context only |
| Local ActionNet | Full governed experience for one institution | none by default |
| Global ActionNet | Approved normalized abstractions with rights and privacy custody | eligible only through a frozen release |
| C1 version registry | Immutable model, dataset, evaluation, predecessor, and disposition lineage | records offline versions; never trains or deploys automatically |

Institutional memory records explicitly return
`scope=INSTITUTION_LOCAL`, `adaptation_mode=CONTEXT_ONLY`,
`training_eligible=false`, and `weight_update_authorized=false`.

## Local-to-global promotion gate

A local experience can be promoted only when it remains non-protected,
training-eligible, overlap-checked, and approved under the existing ActionNet
review workflow. Promotion additionally requires:

- a normalized abstraction with no tenant or local experience identifier;
- no raw payload or authority-bearing field;
- de-identification attestation;
- a registered rights basis and content-hashed rights reference;
- privacy and source-review hashes;
- explicit permitted uses; and
- a one-way commitment to the local source record.

The global record contains the normalized abstraction and source commitment,
not the tenant identity or raw local trajectory. The private local export table
retains the custody mapping. A global release rechecks the current local record,
so later quarantine or overlap failure blocks training.

## C1 version rule

Model generations use versioned names such as `C1-v1` and `C1-v2`. `C2` is
reserved for a future architectural successor rather than an ordinary retrain.

Every C1 version binds a Global ActionNet release, protected evaluation
reservation, artifact, optional adapter, evaluation, license, predecessor, and
safety/performance/transfer gates. Online production updates and
institution-specific weight requirements are rejected. Disposition records are
non-binding governance evidence; they do not load weights, switch traffic, or
execute institutional actions.

## Current boundary

The SQLite reference, schemas, API roles, and fail-closed controls are
implemented. No real institution has approved a contribution, no federated
learning system exists, no model has been trained through this network, and no
production deployment or performance improvement is established.