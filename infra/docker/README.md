# Docker

The CPU service image runs the authenticated EDON and ActionNet Platform API as
a non-root user with a read-only application filesystem and a dedicated state
volume. Never bake secrets, institutional source data, or protected labels into
the image.

```bash
export EDON_API_KEYS='{"replace-with-a-long-admin-token":"ADMIN"}'
docker compose -f infra/docker/compose.yaml up --build
```

Production deployments still require TLS termination, an external identity
provider, a secret manager, encrypted backups, monitoring, migration rehearsal,
penetration testing, and environment-specific approval.