# ActionNet Learning Network

Status: `INTERNAL_GOVERNED_REFERENCE_NOT_PRODUCTION_AUTHORIZED`

In the controlling Cerebrum platform vision, this governed learning reference
feeds an Evaluation and Release Registry. A separate Deployment Controller must
approve installation; an ActionNet release never updates the runtime directly.

This package defines the learning flywheel that separates institution-local
memory and experience from reusable global training data.

```text
Memory -> context-only C1 adaptation
Local ActionNet -> private tenant experience
Promotion gate -> de-identified rights-bound abstraction
Global ActionNet -> qualified reusable experience
Training release -> offline-only frozen dataset identity
C1-vNext -> immutable model and evaluation lineage
Disposition -> shadow/deployment eligibility or rollback record
```

The implementation is `GovernedLearningNetwork` in
`src/edon/actionnet/network.py`. It uses the existing
`ActionNetPlatformStore` as the authoritative local eligibility source.

See `docs/architecture/memory-learning-actionnet.md`, `SECURITY.md`, and
`PRODUCTION_READINESS.md`.