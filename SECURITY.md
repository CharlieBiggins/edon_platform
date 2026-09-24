# Security policy

EDON processes institutional authority, policy, workflow, identity, evidence, and
audit information. Treat all non-synthetic institutional inputs as sensitive.

## Never commit

- credentials, tokens, signing keys, or `.env` files;
- protected institutional documents or logs;
- personally identifiable or regulated records;
- model checkpoints or adapters containing restricted data;
- custodian-only labels or scoring authorization secrets.
- confidential invention disclosures, draft patent claims, legal advice,
  assignments, signatures, private filing data, or actual trade-secret values.

## IP-sensitive information

The public repository may store sanitized candidate-family identifiers, status,
approved public filing metadata, and non-reversible hashes. Store confidential
invention details, counsel records, customer knowledge, training recipes,
protected benchmarks, and trade-secret inventories in a separately controlled
system with need-to-know access, MFA, encryption, logging, and offboarding
revocation.

Before any detailed external disclosure, use the gate in
`docs/ip/PUBLICATION_AND_DISCLOSURE_GATE.md`. Security review does not replace
patent counsel, and filing status does not replace scientific review.

## Reporting

Report suspected vulnerabilities privately to the designated repository security
contact before opening a public issue. Until a contact is configured, do not make
this repository public.

## Authority boundary

Cerebrum outputs are proposals. Binding state transitions require a deterministic
runtime, authorization check, signed commit, and auditable provenance record.

## API access control

The MVP API maps each bearer token to a server-configured role through
`EDON_API_KEYS`; clients cannot select their own role. Use separate random tokens,
TLS termination, a secret manager, network isolation, and rotation in any hosted
environment. The single `EDON_API_KEY` fallback grants `ADMIN` and is suitable
only for isolated development.

The dashboard stores its token in browser local storage. Do not use it on shared
workstations, and do not treat this interface as a substitute for an audited
identity provider.

## Agent Gateway

External agents and vendor platforms are untrusted. Gateway connectors are
tenant-bound, disabled by default, restricted to shadow/read-only modes, and
require operation allowlists, HTTPS endpoints, secret-manager references, and a
security-review reference before enablement. Inline credentials and recursive
authority-bearing fields are rejected. Ingress and staged egress never carry
binding authority.

The repository does not yet implement production identity, secret resolution,
vendor OAuth/SMART lifecycles, raw-body webhook signature verification,
outbound delivery, rate limiting, or managed telemetry export. See
`product/agent-gateway/SECURITY.md` before any connector trial.