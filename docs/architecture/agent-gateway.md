# Agent Gateway architecture

In the controlling platform vision, the Agent Gateway is one protocol family
inside the Observation and Connector Gateway. It cannot mint authorization,
submit arbitrary action content to execution, or treat a delivery receipt as a
verified outcome.

The EDON Agent Gateway is the agent-facing component of the broader
Institutional Environment Gateway. It is a vendor-neutral boundary between
external agent platforms and EDON's non-authoritative reasoning and operations planes. It
normalizes protocol messages, records immutable custody, emits content-minimized
telemetry, and stages proposals without granting external systems execution
authority.

```text
Microsoft · Google · Anthropic · Salesforce · ServiceNow · UiPath
OpenAI · AWS · LangGraph · Epic · Oracle Health · custom agents
                              |
              MCP · A2A · REST/webhooks · FHIR R4/SMART
                              |
                    EDON Agent Gateway
       tenant binding · allowlists · replay protection · audit
                              |
             normalized non-binding gateway envelope
                              |
          Cerebrum / operations / shadow supervision
                              |
             deterministic Kernel authorization boundary
```

## Protocol contracts

The gateway currently targets MCP `2026-07-28`, A2A `1.0`, generic REST and
webhook contracts `1.0`, and FHIR R4 with SMART authorization profiles. Protocol
versions are explicit connector configuration; silent version fallback is not
allowed.

Every connector is tenant-bound, registered disabled, limited to `SHADOW` or
`READ_ONLY`, and restricted by operation and optional target allowlists. An
enabled connector requires an external secret-manager reference and a recorded
security review. Credentials cannot be stored in connector configuration or
message payloads.

## Trust boundary

External messages are untrusted data. The gateway rejects authority-bearing
fields, checks sensitivity ceilings, requires idempotency keys, and records an
immutable content hash. Ingress is marked `ACCEPTED_SHADOW_ONLY`; egress is
marked `STAGED_NOT_DELIVERED`. Neither status means that an action occurred.

The only path to a binding state transition remains a separately authorized,
exact-request Kernel token followed by deterministic commit validation. No
connector, agent card, MCP tool call, A2A task, webhook, or FHIR message can
mint or substitute that authority.

System and resource adapters are intentionally not disguised as agent
connectors. Their broader entity, state-change, time-gating, action-receipt, and
outcome semantics are defined in `institutional-environment-gateway.md`.

## Observability

Each accepted envelope produces an OTLP/HTTP-JSON-compatible span with vendor,
protocol, direction, message type, status, content hash, and size. Message
contents are excluded by default. Trace context accepts W3C `traceparent` and
bounded `tracestate` fields.

## Deliberate limitations

The repository implements the protocol-normalization and custody core, not a
completed production integration for every listed vendor. Native OAuth flows,
vendor SDK clients, Agent Card discovery, MCP session transport, webhook
signature profiles, outbound delivery workers, retries/dead letters, managed
OpenTelemetry export, and vendor conformance suites remain deployment work.

Healthcare connectors are read-only/event-ingress at this boundary. Production
Epic or Oracle Health use additionally requires customer/vendor authorization,
SMART registration, privacy and security review, data minimization, and the
applicable clinical interoperability certification.
