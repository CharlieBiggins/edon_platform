# Vendor integration matrix

All entries are `PROFILE_ONLY_CREDENTIALS_AND_CONFORMANCE_REQUIRED`. “Preferred”
means the protocol-first path EDON should evaluate first; it is not a statement
of certification or complete vendor feature coverage.

| Platform | Preferred EDON path | Additional work before pilot |
| --- | --- | --- |
| OpenAI Agents | MCP, REST | Auth, remote-MCP conformance, tracing, sandbox tests |
| AWS Bedrock AgentCore | A2A, MCP | IAM/workload identity, runtime conformance, tracing |
| Microsoft Agent 365 / Copilot Studio | A2A, MCP | Entra identity, agent registration, governance mapping |
| Google Gemini agent platform | A2A, MCP | Agent Card/identity, Vertex project controls, conformance |
| Anthropic Claude | MCP | OAuth/API identity, tool/resource controls, conformance |
| Salesforce Agentforce | REST, MCP, A2A | Connected app, tenant scopes, event/retry mapping |
| ServiceNow Agent Fabric | A2A, MCP | Instance identity, agent registry, workflow mapping |
| UiPath | MCP, REST/webhooks | Orchestrator identity, robot/process mapping, callbacks |
| LangGraph | A2A, MCP, REST | Application identity, durable-run correlation, callbacks |
| Epic | FHIR R4/SMART | Authorized app, minimum scopes, PHI controls, customer validation |
| Oracle Health Millennium | FHIR R4/SMART | Authorized app, minimum scopes, PHI controls, customer validation |

## Universal fallback

Custom agents should integrate through MCP or A2A when semantics fit, otherwise
through the versioned REST/webhook envelope. OpenTelemetry trace context and
content-minimized gateway spans provide the common observability contract.

Vendor-native adapters should remain thin translations into this same gateway
contract. Vendor code must not be allowed to bypass tenant binding, custody,
shadow supervision, or deterministic Kernel authorization.
