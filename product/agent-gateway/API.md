# Agent Gateway API

All routes except `/health` require a bearer token configured by the service.
Tenant-bound principals cannot select or cross another tenant.

| Endpoint | Permission | Purpose |
| --- | --- | --- |
| `GET /api/gateway/capabilities` | `read` | Return protocol versions and authority limits |
| `GET /api/gateway/vendors` | `read` | Return sanitized vendor capability profiles |
| `POST /api/gateway/connectors` | `gateway_admin` | Register a connector in `DISABLED` state |
| `POST /api/gateway/connectors/status` | `gateway_admin` | Enable, suspend, or disable after review |
| `POST /api/gateway/messages` | `gateway_ingest` | Normalize and record ingress as shadow-only |
| `POST /api/gateway/egress` | `gateway_egress` | Stage egress without delivering it |
| `POST /api/gateway/connectors/query` | `gateway_read` | List tenant-visible connectors |
| `POST /api/gateway/messages/query` | `gateway_read` | List tenant-visible immutable envelopes |
| `POST /api/gateway/audit` | `gateway_admin` | Return tenant-visible audit and whole-chain validity |

## Roles

`GATEWAY_ADMIN` manages connector configuration and audit. `GATEWAY_OPERATOR`
can read, ingest, and stage egress. `GATEWAY_INGRESS` can only read generic
status and submit ingress. `ADMIN` has all gateway permissions.

## Connector lifecycle

Registration rejects inline credentials and always creates a disabled
connector. Enabling requires `credential_secret_ref`, a non-development
authentication method, and `security_review_ref`. Suspending or disabling a
connector preserves configuration, messages, and audit history.

Example connector body:

```json
{
  "connector_id": "microsoft-a2a-primary",
  "tenant_id": "institution-a",
  "vendor_id": "microsoft_agent365_copilot",
  "protocol": "A2A",
  "protocol_version": "1.0",
  "endpoint": "https://agents.example.org/a2a",
  "auth_method": "OAUTH2_CLIENT_CREDENTIALS",
  "credential_secret_ref": "secret://agent-gateway/microsoft-primary",
  "allowed_operations": ["SendMessage", "GetTask", "CancelTask"],
  "allowed_targets": ["edon-shadow-supervisor"],
  "mode": "SHADOW",
  "sensitivity_ceiling": "CONFIDENTIAL",
  "data_residency": "US",
  "binding_authority": false
}
```

The authenticated server overwrites actor identity. Tenant-bound principals
also supply the authoritative tenant identity.

## Message contract

Every message supplies connector and protocol identity, globally meaningful
external message and idempotency keys within its tenant/connector/direction,
an ISO-8601 timestamp with timezone, sensitivity, optional W3C trace context,
and a protocol-specific JSON body. The normalized envelope always contains:

```json
{
  "binding_authority": false,
  "executed": false
}
```

Receipts use `ACCEPTED_SHADOW_ONLY` or `STAGED_NOT_DELIVERED`. Clients must not
interpret either as business-process success.
