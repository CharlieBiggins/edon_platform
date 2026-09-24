# Component map

| Target component | Existing reference foundation | Current target status |
| --- | --- | --- |
| Experience layer | authenticated internal dashboard and API | no production Command Center, cards, SDKs, or public v1 API |
| Institutional Control Graph | world, memory, operations, federation, state, and provenance references | target graph projection and lifecycle ownership not implemented |
| Identity and Capability Registry | operations agent/resource registrations | no complete identity, credential, capability, and revocation service |
| Mandate Service | authority references and Kernel token claims | no scoped delegated-mandate lifecycle |
| Commitment Ledger | goals, plans, memory, and expected outcomes | no complete promise/obligation lifecycle service |
| Resource Reservation System | resource allocation and atomic dispatch references | no target reservation lifecycle or cross-plan conflict service |
| Institutional State Model | five-view Cerebrum state projector | multidimensional target contract specified, not implemented |
| Reasoning Runtime | C1 operations adapter, deterministic provider, planner and solver boundaries | partial internal reference |
| Independent Kernel | exact-request token and world-commit reference | authorization/Execution Assurance separation not implemented |
| Execution Assurance | transactional outbox, dispatch, and outcome references | no separate target service |
| Credential Broker | secret references and bounded connector profiles | no proposal-bound temporary external-credential service |
| Decision and Execution Receipts | execution certificates, cycles, audit, and outbox records | target receipt services not implemented |
| Compensation Manager | cancellation, failure, and replan references | no separately authorized compensation lifecycle |
| Observation and Connector Gateway | Agent Gateway and Institutional Environment Gateway architecture | partial; no production native connectors or delivery workers |
| ActionNet | platform, local/global governance, releases, and experiments | internal reference and bounded research evidence |
| Evaluation and Release Registry | experiment/evaluation manifests and C1 disposition records | fragmented reference; no complete signed target registry |
| Deployment Controller | rollback metadata only | not implemented |
| Runtime monitoring | logs, audit, and bounded telemetry references | no complete containment/rollback control loop |
| Domain packs | synthetic domain and example packages | target manifest specified; no production-qualified pack |
| First Qualified Operational Workflow | no selected customer workflow | not selected or registered |

Historical component identities remain valid. Migration is additive and must
not rewrite experiment artifacts, evaluation records, hashes, or results.

Implementation requirements are registered in
`CEREBRUM-PLATFORM-FOUNDATION-001`. The proposed initial AWS mapping is
`CEREBRUM-AWS-DEPLOYMENT-PROFILE-001`. Both remain drafts and create no
deployment, compliance, production, customer, or consequential-write result.