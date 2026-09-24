# Production-readiness checklist

## Implemented internal controls

- [x] Tenant-isolated persistent product records
- [x] Immutable mechanism, experience, review, exposure, and release records
- [x] Hash-chained tenant audit
- [x] Safe experience defaults
- [x] Protected-vault training exclusion
- [x] Distinct domain and safety reviewers
- [x] Required lineage/training/privacy review dimensions
- [x] Protected-overlap gate
- [x] Content-bound training releases
- [x] Authenticated role separation
- [x] Non-root read-only container definition
- [x] Internal deterministic product evaluation
- [x] Canonical Institutional IR with closed references and tuple mapping
- [x] Executable composition with deterministic replay
- [x] Replay-verified active counterfactual generation
- [x] First-class temporal and epistemic state
- [x] Assumption-bounded human-behavior scenarios
- [x] Governed abstraction intake with raw-sensitive field rejection
- [x] Institution-local memory is context-only and cannot authorize weight updates
- [x] Tenant-local ActionNet remains the authoritative experience source
- [x] Global promotion requires de-identification, rights, privacy, provenance,
  overlap, and local-eligibility checks
- [x] Global training releases are immutable and offline-only
- [x] C1 versions bind dataset, artifact, protected-evaluation, and predecessor
  lineage
- [x] C1 shadow/deployment dispositions fail closed on safety, performance, and
  transfer gates
- [x] Automatic, online, and institution-specific weight updates are rejected

## Required before production authorization

- [ ] External OIDC/workload identity and lifecycle management
- [ ] TLS termination and certificate rotation
- [ ] Managed secret storage and token/key rotation
- [ ] Production database migration and rollback rehearsal
- [ ] Encrypted backup, restore, retention, and disaster-recovery tests
- [ ] Multi-replica concurrency and availability validation
- [ ] Rate limits, quotas, abuse controls, and request-size policy
- [ ] Structured metrics, tracing, alerting, and SIEM audit export
- [ ] Tenant deletion, export, residency, and legal-hold procedures
- [ ] Privacy impact assessment and contractual data-rights review
- [ ] Customer-edge DLP, de-identification, and abstraction validation
- [ ] Independent legal confirmation of every Global ActionNet contribution's
  permitted use and retention basis
- [ ] External re-identification testing and privacy red-team assessment
- [ ] Independently custodied protected evaluation for each deployable C1 version
- [ ] Model rollback, revocation propagation, and multi-tenant isolation drills
- [ ] Evidence that Global ActionNet improves C1 without degrading safety or
  unseen-institution transfer
- [ ] Calibrated behavioral models with approved domain-specific use boundaries
- [ ] External validation of composition and counterfactual fidelity
- [ ] Dependency/container scanning and signed build provenance
- [ ] Independent penetration test and remediation
- [ ] Incident response and operator runbooks
- [ ] Source-grounded design-partner pilot in shadow mode
- [ ] Formal production release authorization

Status: `INTERNAL_MVP_NOT_PRODUCTION_READY`.