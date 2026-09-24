# Production-readiness checklist

Current disposition: `INTERNAL_PROTOCOL_CORE_NOT_PRODUCTION_AUTHORIZED`.

## Implemented internal controls

- [x] Protocol-version-pinned MCP, A2A, REST/webhook, and FHIR normalization
- [x] Tenant-scoped connector and message identities
- [x] Disabled-by-default connectors
- [x] Security-review and secret-reference enablement gate
- [x] HTTPS-only connector endpoints
- [x] Operation and target allowlists
- [x] Sensitivity ceilings and one-MiB normalized payload limit
- [x] Credential and authority-field rejection
- [x] Immutable envelopes and audit events
- [x] Content hashing, idempotency, and replay protection
- [x] Content-minimized OTLP-compatible telemetry construction
- [x] Read-only/event-ingress FHIR boundary
- [x] Separate gateway administration, operation, and ingress roles
- [x] Non-binding ingress and non-delivering egress statuses
- [x] Kernel authorization remains outside the gateway
- [x] Automated MCP, A2A, REST, webhook, FHIR, API-role, tenant, audit, and
  safety tests

## Required before any production pilot

- [ ] Select one design partner and one narrowly scoped shadow workflow
- [ ] Complete vendor-specific protocol and API conformance tests
- [ ] Implement OIDC/workload identity and managed secret resolution
- [ ] Implement vendor OAuth/SMART lifecycle, consent, revocation, and rotation
- [ ] Implement raw-body webhook signature verification per vendor
- [ ] Implement an outbound delivery worker with durable queue, backoff,
  dead-letter handling, reconciliation, and operator controls
- [ ] Implement actual OTLP export, dashboards, alerts, and trace retention
- [ ] Add API gateway rate limits, quotas, WAF controls, and request timeouts
- [ ] Add production database migrations, encryption, HA, backup, and restore
- [ ] Add DLP, malware/content scanning, retention, deletion, and legal holds
- [ ] Complete privacy, data-rights, residency, and incident-response reviews
- [ ] Complete an independent penetration test and remediate findings
- [ ] Run fault injection, load, replay, failover, and disaster-recovery tests
- [ ] For healthcare, complete SMART registration and all applicable clinical,
  privacy, security, and contractual approvals
- [ ] Obtain formal release authorization with rollback owners and stop criteria

## Recommended rollout

1. REST/webhook or MCP shadow ingress with synthetic data.
2. Vendor sandbox with read-only data and no egress delivery.
3. Customer-controlled shadow pilot with complete telemetry and human review.
4. Staged non-binding egress recommendations with reconciliation.
5. Only after separate safety and operational evidence, permit narrowly scoped
   Kernel-authorized commits; the gateway itself never gains binding authority.
