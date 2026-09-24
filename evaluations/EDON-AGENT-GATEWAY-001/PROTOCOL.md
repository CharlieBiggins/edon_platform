# Protocol

The evaluation creates fresh temporary SQLite custody, registers disabled MCP
and FHIR connectors, enables them with review and secret references, records a
valid MCP ingress, repeats it, attacks the idempotency and authority boundaries,
attempts cross-tenant access and a FHIR write, checks immutability and audit,
and inspects telemetry and vendor-profile claim limits.

All checks must pass. The result is deterministic and contains no external
network call or vendor credential.