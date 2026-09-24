# Deployment runbook

This runbook permits sandbox and shadow deployment only. It does not authorize
binding production operation.

## 1. Infrastructure prerequisites

- approved TLS ingress and private service networking;
- external OIDC/workload identity mapped to EDON gateway roles;
- managed secret store capable of resolving the configured `secret://` names;
- production database, encrypted backups, tested restore, and migration owner;
- durable broker for future delivery work, with retries and dead letters;
- OTLP collector, dashboards, alerts, SIEM export, and retention policy;
- rate limits, WAF/content limits, DLP, malware scanning, and incident contacts.

## 2. Connector onboarding

1. Select one vendor, tenant, protocol version, workflow, data class, and
   shadow-only success criterion.
2. Complete identity, authorization, privacy, data-rights, residency, threat,
   and vendor-conformance reviews.
3. Provision credentials in the managed secret store; put only the secret
   reference in EDON.
4. Register an HTTPS connector with the minimum operation and target allowlists.
5. Confirm it remains `DISABLED`, record the approved security-review reference,
   then enable it through a `GATEWAY_ADMIN` identity.
6. Send synthetic canaries, test replay and revocation, verify audit and traces,
   then admit minimized sandbox data.
7. Define stop conditions and suspend the connector on any identity, scope,
   custody, privacy, delivery, or reconciliation failure.

## 3. Promotion gates

Sandbox-to-shadow promotion requires vendor conformance, load/fault tests,
observability, security review, and an approved data-flow diagram. Shadow-to-
staged-egress promotion additionally requires reconciliation and human review.
No gateway promotion grants execution authority; any commit still requires the
separate Kernel path.

Epic and Oracle Health onboarding remains FHIR read-only/event-ingress until
SMART registration, customer authorization, minimum-necessary scopes, and all
applicable privacy, security, clinical, and contractual controls are complete.

## 4. Rollback

Set the connector status to `SUSPENDED`, revoke upstream credentials, stop
delivery workers, preserve immutable custody and external logs, reconcile all
in-flight identifiers, and follow the incident plan. Do not delete gateway
messages or audit events during rollback.
