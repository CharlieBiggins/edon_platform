# Persistent Managed Staging v1

This Terraform root provisions the staging reference profile:

- private RDS PostgreSQL 16 with Multi-AZ, encryption and point-in-time backups;
- ECS Fargate API and separate outbox worker services in private subnets;
- a one-shot migrator task definition with its own IAM role;
- asymmetric KMS signing, encrypted S3 evidence storage and Secrets Manager;
- TLS ALB ingress, optional Route 53 alias, WAF rate limiting and CloudWatch alarms;
- GitHub Actions OIDC deployment role with no long-lived AWS credentials.

The intended staging application hostname is `https://app.edoncore.com`. Set
`route53_zone_id` to the authoritative `edoncore.com` hosted zone and provide
an ACM certificate covering `app.edoncore.com` before applying. The hostname
does not become live until the stack is provisioned and DNS is delegated.

Before applying, populate the runtime secret with a PostgreSQL URL whose database
roles are `cerebrum_migrator`, `cerebrum_app` and `cerebrum_audit`. The OIDC
issuer and JWKS URL must be a real provider. `RUNTIME_PROFILE=STAGING` prevents
the simulated identity and deterministic signing providers from being selected.

The stack intentionally contains no customer data and no production connector
credentials. Dispatch remains disabled until a separately qualified connector
credential provider is configured.

Deployment order is: apply infrastructure, write the runtime secret, run the
migrator task, verify `/healthz` and `/readyz`, then run the managed staging
qualification workflow and restore drill. Keep Terraform state in an encrypted,
locked remote backend before using this outside an isolated account.
