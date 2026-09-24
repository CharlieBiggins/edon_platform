# Control Plane API runtime profiles

`LOCAL` is the only profile that permits memory repositories, simulated identity and deterministic hash custody.

`STAGING_TEST`, `STAGING` and `PRODUCTION` fail during startup unless PostgreSQL-shaped repositories, OIDC verification, KMS-shaped custody, tenant isolation and audit logging are supplied through dependency injection. `STAGING_TEST` permits ephemeral local providers that implement those same interfaces.

The migration directory is the source of truth for production schema changes. `schema.sql` is retained as a reference snapshot only.
