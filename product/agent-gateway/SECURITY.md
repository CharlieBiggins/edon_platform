# Agent Gateway security model

## Hard invariants

- External agents are untrusted and non-authoritative.
- Connector and message access is tenant-scoped.
- New connectors are disabled and cannot be enabled without a security-review
  reference and secret-manager reference.
- Only HTTPS endpoints are accepted; URL-embedded credentials are rejected.
- Inline tokens, passwords, private keys, API keys, and client secrets are
  rejected from connector records and untrusted payloads.
- Operation and target allowlists are evaluated before custody.
- Authority, execution-token, commit, and binding-eligibility fields are
  rejected recursively.
- Message and audit records are immutable; duplicate idempotency keys cannot be
  rebound to different content.
- Telemetry excludes payload contents by default.
- FHIR create, update, patch, delete, transaction, and batch operations are
  blocked at the gateway.

## Deployment controls still required

A production deployment must terminate TLS at an approved edge, use OIDC or
workload identity, resolve `secret://` references through a managed secret
store, rotate keys, verify vendor-specific webhook signatures over the original
request bytes, apply network egress controls, enforce quotas/rate limits, scan
payloads for malware and sensitive-data policy, and export logs and traces to a
monitored SIEM/observability system.

Each vendor connector needs a dedicated threat model covering token audience,
scope, consent, agent identity, confused-deputy risk, SSRF, prompt/tool
injection, callback validation, replay windows, and revocation behavior.

## Healthcare

Do not send production PHI through the reference service. Epic and Oracle
Health integrations require authorized applications, minimum-necessary scopes,
SMART/OAuth validation, tenant-specific data residency and retention, audit
export, incident response, and applicable contractual and regulatory review.
Clinical recommendations remain proposals and cannot bypass human review or
the Kernel authorization boundary.

## Incident action

Suspend the affected connector first. Suspension stops new gateway custody but
does not delete evidence. Preserve the connector configuration hash, relevant
message hashes, audit chain, identity-provider logs, secret-manager access logs,
and upstream/downstream traces for investigation.
