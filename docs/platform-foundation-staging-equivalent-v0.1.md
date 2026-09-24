# Cerebrum Platform Foundation — Staging-Equivalent Baseline v0.1

**Baseline tag:** `platform-foundation-v0.1`

**Commit:** `3992a509fd2fbd4ff6d1884129d0ecbad755dccc`

**Required branch check:** `staging-validation` on `master` (strict status enforcement enabled).

**Preserved validation artifact:** [staging-validation-artifacts](https://github.com/CharlieBiggins/edon_platform/actions/runs/36038495431/artifacts/10825314821)

## What the suite proves

- The compiled Control Plane API starts under the staging-shaped runtime profile.
- PostgreSQL migrations apply with stop-on-error and the expected migration sequence.
- The lifecycle can be exercised through HTTP contracts.
- Events, evidence, proposals, reviews, Kernel decisions, shadow evaluations, outcomes and receipts persist through the repository boundary.
- State and reconstruction remain stable across API restart and database backup/restore checks.
- OIDC/JWKS token verification rejects invalid issuer, audience, expiry and malformed credentials.
- Tenant isolation and append-only permissions are tested with restricted application and audit roles.
- Reconstruction access is role-bound to auditor/investigator principals.
- Shadow evaluation has no dispatch path or customer write credentials.
- Durability snapshots, receipt data and reconstruction hashes are compared before and after restart and restore.

## What remains simulated

- The OIDC issuer is a temporary CI issuer, not a customer identity provider.
- Receipt signing uses the staging-test cryptographic provider, not cloud KMS custody.
- PostgreSQL runs as an ephemeral CI service, not managed persistent staging PostgreSQL.
- Connector observations, institutional data and logistics outcomes are controlled fixtures.
- The Command Center still contains simulated surfaces outside the INC-1042 shadow path.
- No customer-system credentials, production writes or operational execution are enabled.
- Cloud logging, monitoring, disaster recovery and load infrastructure are not represented by this CI job.

This document freezes the CI foundation. Change it only to correct a real defect in the validation contract.
