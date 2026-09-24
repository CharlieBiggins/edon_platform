# EDON Agent Gateway

Status: `INTERNAL_PROTOCOL_CORE_NOT_PRODUCTION_AUTHORIZED`

The Agent Gateway is the agent-facing component of EDON's broader Institutional
Environment Gateway. It gives EDON one governed integration boundary for
enterprise agents instead of embedding vendor behavior inside Cerebrum. Its universal
surface is MCP, A2A, REST/webhooks, OpenTelemetry, and read-only FHIR R4/SMART.
Vendor profiles cover OpenAI, AWS Bedrock AgentCore, Microsoft Agent 365 and
Copilot Studio, Google Gemini's agent platform, Anthropic Claude, Salesforce
Agentforce, ServiceNow Agent Fabric, UiPath, LangGraph, Epic, and Oracle Health.

## Implemented now

- explicit MCP `2026-07-28`, A2A `1.0`, REST/webhook, and FHIR R4 contracts;
- tenant-scoped connector identities and data access;
- disabled-by-default connector registration and review-gated enablement;
- secret-manager references without stored credential values;
- per-connector operation and target allowlists;
- strict HTTPS endpoint validation and sensitivity ceilings;
- protocol normalization into immutable non-binding envelopes;
- idempotency, replay protection, content hashes, and hash-chained audit;
- authority-field and credential-field rejection;
- read-only/event-ingress healthcare boundary with FHIR writes blocked;
- OTLP-compatible, content-minimized telemetry records;
- authenticated API roles for administration, ingress, egress staging, and read;
- egress staging that never implies delivery or execution.

## Not implemented or certified

- native vendor SDK clients or vendor marketplace packages;
- production OAuth/SMART exchanges, mTLS provisioning, or key rotation;
- webhook signature verification profiles for individual vendors;
- live Agent Card discovery or complete MCP/A2A network transports;
- outbound delivery workers, queues, retry policy, or dead-letter handling;
- a managed OpenTelemetry exporter and production alerting;
- external identity-provider integration, rate limiting, HA, or DR validation;
- vendor conformance, penetration, privacy, clinical, or real-institution tests.

The profiles in `VENDOR_MATRIX.md` are implementation targets, not claims that
EDON is certified by, affiliated with, or production-tested against those
vendors.

## Runtime boundary

Ingress becomes an immutable shadow-only envelope. Egress is staged but not
sent. Any later binding action must be separately proposed, reviewed as
required, authorized with an exact-request Kernel token, and committed by the
deterministic execution plane.

See `API.md`, `SECURITY.md`, `DEPLOYMENT.md`, and `PRODUCTION_READINESS.md`
before configuring a connector. The umbrella agent/system/resource design is
documented in `product/institutional-environment-gateway/`.