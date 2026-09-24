# Production-readiness checklist

## Implemented internal reference controls

- [x] Institution-local memory is context-only and non-training by default.
- [x] Local ActionNet experience remains tenant isolated.
- [x] Promotion revalidates local review, protection, overlap, and eligibility.
- [x] Global records contain normalized abstractions rather than raw payloads.
- [x] Rights, privacy, source, and permitted-use commitments are content bound.
- [x] Global training releases are immutable and offline-only.
- [x] C1 versions reject automatic, online, and institution-specific updates.
- [x] Model lineage binds the training release, artifact, protected evaluation,
  predecessor, and evidence gates.
- [x] Shadow, deployment, rollback, revocation, and archive dispositions are
  append-only and non-binding.

## Required before production authorization

- [ ] Contractual and legal review for each contribution source and permitted use.
- [ ] Independently validated de-identification and re-identification testing.
- [ ] Production DLP, secret scanning, sensitive-field classifiers, and incident
  response.
- [ ] Institution deletion, revocation, legal hold, retention, and export flows.
- [ ] Encrypted backup, restoration, concurrency, and disaster-recovery testing.
- [ ] Independent protected evaluations for safety, performance, transfer, and
  regression across institutions and domains.
- [ ] Signed model artifacts, software bill of materials, reproducible builds,
  and deployment attestation.
- [ ] Operational rollback drills and proof that revocation reaches every serving
  environment.
- [ ] Source-grounded shadow pilots with approved institutions.
- [ ] Formal production release authorization.

No real-institution contribution, federated-learning result, trained C1 model,
privacy validation, transfer result, production authorization, or binding
authority is established by this reference implementation.