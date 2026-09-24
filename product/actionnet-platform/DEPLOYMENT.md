# Deployment

## Internal Docker deployment

```bash
export EDON_API_KEYS='{"replace-with-a-long-admin-token":"ADMIN"}'
docker compose -f infra/docker/compose.yaml up --build
```

The service listens on host loopback port 8080 and stores SQLite state in the
`edon-state` volume. The container runs without Linux capabilities, with
`no-new-privileges`, a read-only application filesystem, and a non-root user.

## Required production topology

```text
TLS ingress / WAF
       ↓
OIDC or workload identity
       ↓
ActionNet API replicas
       ↓
durable transactional database
       ↓
encrypted object custody + backup
       ↓
audit/SIEM export and monitoring
```

SQLite is appropriate for the internal single-node MVP. A production migration
must preserve immutable identities, tenant isolation, append-only governance,
unique review constraints, content hashes, and audit-chain verification.