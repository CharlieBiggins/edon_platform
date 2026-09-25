# Persistent Managed Staging v1 audit

Status: **BLOCKED — READY_TO_APPLY not granted**

This review is intentionally plan-only. No `terraform apply` has been run.

## Required checks

The deployment workflow must run, in order:

```text
terraform fmt -check
terraform init -backend-config=...
terraform validate
tflint --recursive
checkov -d infra/aws/staging
terraform plan -out=tfplan
```

The plan must have no unresolved variables. The backend must be an encrypted,
versioned S3 bucket with a DynamoDB lock table. The backend configuration is
supplied out of band and never stored in this repository.

## Findings before provisioning

1. **KMS rotation corrected.** Automatic rotation is disabled for the
   asymmetric signing key. Rotation is performed by creating a new key,
   updating the alias, retaining the old key ID/public key and recording an
   immutable governance event. Historical receipt verification must use the
   retained key version.
2. **External validation is still required.** Terraform, TFLint and Checkov
   are not installed in this development environment, so no reviewed plan or
   static-analysis result exists yet.
3. **Runtime secret is required.** The Secrets Manager value must be populated
   with a PostgreSQL URL using the application role before ECS starts.
4. **Migration gating must be enforced by the release controller.** The
   migrator task must complete and migration version verification must pass
   before updating the API service.
5. **No customer data or production dispatch is permitted.**

## Network and identity audit

ECS tasks use private subnets and controlled NAT for ECR, Secrets Manager,
CloudWatch, KMS and the external OIDC/JWKS provider. The production hardening
follow-up should add interface VPC endpoints for ECR, Secrets Manager, KMS,
CloudWatch Logs and S3 gateway endpoints, then restrict NAT egress to the
identity provider and required AWS endpoints.

RDS is private, has no public endpoint, is restricted to the API security group,
uses encrypted storage and has seven-day backups plus deletion protection.
API, worker and migrator have distinct task/database roles. GitHub OIDC is
restricted to the protected `master` branch of the configured repository.

## Estimated monthly cost

Indicative us-east-1 baseline, excluding data transfer and provider-specific
OIDC/WAF usage:

| Component | Estimate |
|---|---:|
| Multi-AZ db.t4g.small RDS, 50 GB, backups | $55–90 |
| Two API Fargate tasks | $25–45 |
| One worker Fargate task | $8–15 |
| NAT gateways (two AZ) | $65–100 |
| ALB, WAF and CloudWatch | $35–75 |
| S3, KMS, Secrets Manager, Route 53 | $5–20 |
| **Estimated total** | **$193–345/month** |

Obtain a current AWS Pricing Calculator export before approval; these figures
are not a billing commitment.

## Required configuration and secrets

- AWS region and encrypted remote Terraform backend
- GitHub OIDC deployment role ARN
- ECR API and worker image URIs
- Real OIDC issuer, audience and JWKS URL
- ACM certificate ARN and optional Route 53 zone/hostname
- Secrets Manager `DATABASE_URL` containing the application connection string
- Separate migrator, application and audit database roles
- Operator and auditor staging tokens for post-deployment validation
- `CEREBRUM_STAGING_ENABLED=true` and `CEREBRUM_STAGING_URL`

## Deployment and rollback

1. Run the plan-only qualification workflow and review `tfplan`, TFLint,
   Checkov, IAM and cost reports.
2. Apply the network, data, key, secret and ECS task infrastructure.
3. Populate the runtime secret without committing its value.
4. Run the dedicated migrator task; stop on migration error and do not deploy
   or update API tasks.
5. Verify migration version, `/healthz`, `/readyz`, RLS and KMS signing.
6. Deploy API and worker with ECS deployment circuit breakers enabled.
7. Run staging lifecycle, crash-recovery, restore, OIDC and tenant-isolation
   tests; publish a machine-readable report.
8. Roll back by restoring the previous ECS task definition/image. Database
   migrations require a forward-compatible corrective migration or a tested
   point-in-time restore; never silently downgrade schema state.

## Manual KMS rotation

1. Create a new asymmetric `RSA_4096` `SIGN_VERIFY` key.
2. Grant signing only to the API/worker task roles; grant verification to
   readers and investigators as policy permits.
3. Update the staging signing alias to the new key.
4. Record `KMS_KEY_ROTATED` with old/new key IDs, operator, reason and time in
   the append-only governance journal.
5. Keep the previous key enabled for verification and retain its public key
   metadata until all receipts pass retention and legal-hold periods.
6. Independently verify old and new receipts, then disable the old key only
   through a separately approved retirement procedure.
