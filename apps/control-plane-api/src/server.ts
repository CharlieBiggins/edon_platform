import { createServer, type IncomingMessage, type ServerResponse } from 'node:http';
import { CONTRACT_VERSION, openApiDocument, validateBinding, type RequestBinding } from '../../../packages/contracts/src/index.js';
import { DeterministicEvidenceAdmission } from '../../../packages/platform-core/src/evidence-admission.js';
import { DeterministicKernel } from '../../../packages/platform-core/src/kernel.js';
import { LogisticsProposalGenerator } from '../../../packages/platform-core/src/proposal-generator.js';
import { ReplayableStateProjector } from '../../../packages/platform-core/src/state-projector.js';
import { HumanReviewGate } from '../../../packages/platform-core/src/human-review.js';
import { ShadowEvaluator } from '../../../packages/platform-core/src/shadow-evaluator.js';
import { SimulatedIdentityVerifier, type IdentityVerifier } from '../../../packages/platform-core/src/auth.js';
import { InMemoryPlatformRepositories } from '../../../packages/platform-core/src/repositories.js';
import { HashLinkedReceiptService } from '../../../packages/platform-core/src/receipt-service.js';
import { KmsReceiptCustody, type ReceiptSigner } from '../../../packages/platform-core/src/receipt-custody.js';
import { assertRuntimeProfile, type RuntimeDependencies, type RuntimeProfile } from './runtime.js';

const repositories = new InMemoryPlatformRepositories();
const state = async (repositories: RuntimeDependencies['repositories'], tenantId: string, scopeId: string) => new ReplayableStateProjector().project(await repositories.getEvents(tenantId, undefined).then(events => events.filter(event => event.scope_id === scopeId)));
const json = (request: IncomingMessage) => new Promise<Record<string, unknown>>((resolve, reject) => { let body = ''; request.on('data', chunk => { body += chunk; }); request.on('end', () => { try { resolve(body ? JSON.parse(body) : {}); } catch { reject(new Error('invalid json')); } }); });
const reply = (response: ServerResponse, status: number, body: unknown) => { response.statusCode = status; response.setHeader('content-type', 'application/json'); response.end(JSON.stringify(body)); };
const failure = (response: ServerResponse, code: string, message: string, correlation_id = 'unknown') => reply(response, code === 'INTERNAL_ERROR' ? 500 : code === 'VALIDATION_FAILED' ? 400 : code === 'PERMISSION_DENIED' ? 403 : code === 'STATE_STALE' ? 409 : 422, { error: { code, message, correlation_id } });
const binding = (body: Record<string, unknown>) => body.binding as RequestBinding | undefined;
const validateRequest = (body: Record<string, unknown>) => validateBinding(binding(body));

export type ControlPlaneServerOptions = Partial<RuntimeDependencies> & { profile?: RuntimeProfile; identityVerifier?: IdentityVerifier; receiptSigner?: ReceiptSigner; corsOrigin?: string };
export function createControlPlaneServer(options: ControlPlaneServerOptions = {}) {
  const profile = options.profile ?? 'LOCAL';
  const identityVerifier = options.identityVerifier ?? new SimulatedIdentityVerifier({ tenant_id: 'meridian-demo', actor_id: 'operator-01', actor_type: 'HUMAN', roles: ['operator'], expires_at: '2099-01-01T00:00:00Z' });
  const runtimeDependencies: RuntimeDependencies = { repositories: options.repositories ?? repositories, identityVerifier, receiptSigner: options.receiptSigner ?? new KmsReceiptCustody(), tenantIsolation: options.tenantIsolation ?? profile === 'LOCAL', auditLogging: options.auditLogging ?? profile === 'LOCAL', signingKeyMode: options.signingKeyMode ?? 'DEVELOPMENT' };
  assertRuntimeProfile(profile, runtimeDependencies);
  return createServer(async (request, response) => {
    try {
    const origin = request.headers.origin;
    if (origin && origin === options.corsOrigin) response.setHeader('access-control-allow-origin', origin);
    response.setHeader('vary', 'Origin');
    if (request.method === 'OPTIONS') { response.setHeader('access-control-allow-headers', 'authorization,content-type,x-correlation-id,x-trace-id'); response.setHeader('access-control-allow-methods', 'GET,POST,OPTIONS'); return reply(response, 204, null); }
    const url = new URL(request.url ?? '/', 'http://localhost');
    if (request.method === 'GET' && url.pathname === '/openapi.json') return reply(response, 200, openApiDocument());
    let body: Record<string, unknown> = {};
    try { if (request.method === 'POST') body = await json(request); } catch { return failure(response, 'VALIDATION_FAILED', 'Request body must be valid JSON'); }
    const bind = binding(body);
    if (request.method === 'GET' && url.pathname === '/healthz') return reply(response, 200, { status: 'ok', profile });
    if (request.method === 'GET' && url.pathname === '/readyz') return reply(response, profile === 'LOCAL' || (runtimeDependencies.tenantIsolation && runtimeDependencies.auditLogging) ? 200 : 503, { status: profile === 'LOCAL' ? 'ready-simulated' : 'ready' });
    const principal = await runtimeDependencies.identityVerifier.verify(request);
    const authenticatedRoute = url.pathname.startsWith('/v1/');
    if (authenticatedRoute && !principal) return reply(response, 401, { error: { code: 'AUTHENTICATION_REQUIRED', message: 'Authentication is required', correlation_id: request.headers['x-correlation-id'] ?? 'unknown' } });
    if (request.method === 'POST' && principal && bind && (bind.tenant_id !== principal.tenant_id || bind.actor_id !== principal.actor_id)) return failure(response, 'PERMISSION_DENIED', 'Request identity does not match verified identity', principal.actor_id);
    if (request.method === 'POST' && (!validateRequest(body) || bind?.contract_version !== CONTRACT_VERSION)) return failure(response, 'VALIDATION_FAILED', 'Required request binding is missing or invalid', bind?.correlation_id);
    const currentState = bind ? await state(runtimeDependencies.repositories, principal?.tenant_id ?? bind.tenant_id, String(body.scope_id ?? 'memphis-fulfillment')) : { version: 141, values: {} };
    if (request.method === 'POST' && bind?.expected_state_version !== undefined && bind.expected_state_version !== currentState.version) return failure(response, 'STATE_STALE', 'Expected state version is stale', bind.correlation_id);
    if (request.method === 'POST' && url.pathname === '/v1/events') {
      const event = { event_id: String(body.event_id ?? `evt-${Date.now()}`), tenant_id: bind!.tenant_id, event_type: 'OBSERVATION_RECEIVED' as const, actor_id: bind!.actor_id, actor_type: 'CONNECTOR' as const, scope_id: String(body.scope_id ?? 'memphis-fulfillment'), incident_id: String(body.incident_id ?? 'INC-1042'), occurred_at: bind!.request_timestamp, observed_at: bind!.request_timestamp, available_to_controller_at: bind!.request_timestamp, recorded_at: bind!.request_timestamp, correlation_id: bind!.correlation_id, trace_id: bind!.trace_id, state_version_before: currentState.version, state_version_after: currentState.version, policy_version: 'POL-LOG-07 v18', payload: (body.payload ?? {}) as Record<string, unknown>, payload_hash: 'sha256:api', previous_record_hash: 'sha256:api', signature: 'simulated', simulated: true as const };
      const idempotency = await runtimeDependencies.repositories.claimIdempotency(principal!.tenant_id, `POST:/v1/events:${bind!.idempotency_key}`, event);
      if (!idempotency.claimed) return reply(response, 200, { data: idempotency.response, meta: { correlation_id: bind!.correlation_id, contract_version: CONTRACT_VERSION } });
      const appended = await runtimeDependencies.repositories.appendEvent(event);
      if (!appended) return reply(response, 200, { data: event, meta: { correlation_id: bind!.correlation_id, contract_version: CONTRACT_VERSION } });
      const projected = await state(runtimeDependencies.repositories, bind!.tenant_id, event.scope_id);
      await runtimeDependencies.repositories.putState({ tenant_id: bind!.tenant_id, incident_id: event.incident_id, scope_id: event.scope_id, state_version: projected.version, status: 'OPEN', values: projected.values }, currentState.version);
      return reply(response, 201, { data: event, meta: { correlation_id: bind!.correlation_id, contract_version: CONTRACT_VERSION } });
    }
    if (request.method === 'POST' && url.pathname === '/v1/proposals') { const evidence = new DeterministicEvidenceAdmission().admit({ event: 'capacity_disruption' }); for (const record of evidence) await runtimeDependencies.repositories.putEvidence({ ...record, tenant_id: bind!.tenant_id }); const proposal = new LogisticsProposalGenerator().create(currentState, evidence); await runtimeDependencies.repositories.putIncident({ tenant_id: bind!.tenant_id, incident_id: proposal.incident_id, scope_id: String(body.scope_id ?? 'memphis-fulfillment'), state_version: currentState.version, status: 'OPEN' }); await runtimeDependencies.repositories.putProposal({ ...proposal, tenant_id: bind!.tenant_id }); return reply(response, 201, { data: proposal, meta: { correlation_id: bind!.correlation_id, contract_version: CONTRACT_VERSION } }); }
    if (request.method === 'POST' && url.pathname === '/v1/reviews') { const proposal = await runtimeDependencies.repositories.getProposal(bind!.tenant_id, String(body.proposal_id)); if (!proposal) return failure(response, 'VALIDATION_FAILED', 'Proposal not found', bind?.correlation_id); const decision = new HumanReviewGate().reevaluate(proposal, body.approved === true, currentState.version, 30000); await runtimeDependencies.repositories.putKernelDecision({ ...decision, tenant_id: bind!.tenant_id, recorded_at: bind!.request_timestamp }); await runtimeDependencies.repositories.putReview({ tenant_id: bind!.tenant_id, review_id: `review-${proposal.proposal_id}`, proposal_id: proposal.proposal_id, actor_id: bind!.actor_id, approved: body.approved === true, recorded_at: bind!.request_timestamp }); return reply(response, 200, { data: decision, meta: { correlation_id: bind!.correlation_id, contract_version: CONTRACT_VERSION } }); }
    if (request.method === 'POST' && url.pathname === '/v1/shadow-evaluations') { const proposal = await runtimeDependencies.repositories.getProposal(bind!.tenant_id, String(body.proposal_id)); if (!proposal) return failure(response, 'VALIDATION_FAILED', 'Proposal not found', bind?.correlation_id); const shadow = new ShadowEvaluator().record(proposal); await runtimeDependencies.repositories.putShadow({ proposal_id: shadow.proposal_id, recorded_at: shadow.recommendation_recorded_at, executed: false, credentials: 'NONE', tenant_id: bind!.tenant_id }); return reply(response, 201, { data: shadow, meta: { correlation_id: bind!.correlation_id, contract_version: CONTRACT_VERSION } }); }
    if (request.method === 'POST' && url.pathname === '/v1/outcomes') { const proposal = await runtimeDependencies.repositories.getProposal(bind!.tenant_id, String(body.proposal_id)); const decision = proposal ? await runtimeDependencies.repositories.getKernelDecision(bind!.tenant_id, proposal.proposal_id) : null; if (proposal && decision) { const receipt = new HashLinkedReceiptService().issue(proposal, decision, body as never); await runtimeDependencies.repositories.putReceipt({ ...receipt, tenant_id: bind!.tenant_id }); } await runtimeDependencies.repositories.putOutcome(Object.assign({}, body, { tenant_id: bind!.tenant_id }) as never); return reply(response, 201, { data: body, meta: { correlation_id: bind!.correlation_id, contract_version: CONTRACT_VERSION } }); }
    const tenantId = principal?.tenant_id ?? bind?.tenant_id;
    if (request.method === 'GET' && url.pathname.startsWith('/v1/reconstructions/') && !principal?.roles.some(role => role === 'auditor' || role === 'investigator')) return failure(response, 'PERMISSION_DENIED', 'Reconstruction access requires an auditor or investigator role');
    if (request.method === 'GET' && url.pathname.startsWith('/v1/state/')) return reply(response, 200, { data: await state(runtimeDependencies.repositories, tenantId!, url.pathname.split('/').at(-1) ?? ''), meta: { correlation_id: request.headers['x-correlation-id'] ?? 'read', contract_version: CONTRACT_VERSION } });
    if (request.method === 'GET' && url.pathname.startsWith('/v1/incidents/')) return reply(response, 200, { data: { incident_id: url.pathname.split('/').at(-1), state: await state(runtimeDependencies.repositories, tenantId!, 'memphis-fulfillment'), proposal_ids: [] }, meta: { correlation_id: 'read', contract_version: CONTRACT_VERSION } });
    if (request.method === 'GET' && url.pathname.startsWith('/v1/receipts/')) return reply(response, 200, { data: await runtimeDependencies.repositories.getReceipt(tenantId!, url.pathname.split('/').at(-1) ?? ''), meta: { correlation_id: 'read', contract_version: CONTRACT_VERSION } });
    if (request.method === 'GET' && url.pathname.startsWith('/v1/proposals/')) return reply(response, 200, { data: await runtimeDependencies.repositories.getProposal(tenantId!, url.pathname.split('/').at(-1) ?? ''), meta: { correlation_id: 'read', contract_version: CONTRACT_VERSION } });
    if (request.method === 'GET' && url.pathname.startsWith('/v1/decisions/')) return reply(response, 200, { data: await runtimeDependencies.repositories.getKernelDecision(tenantId!, url.pathname.split('/').at(-1) ?? ''), meta: { correlation_id: 'read', contract_version: CONTRACT_VERSION } });
    if (request.method === 'GET' && url.pathname.startsWith('/v1/outcomes/')) return reply(response, 200, { data: await runtimeDependencies.repositories.getOutcome(tenantId!, url.pathname.split('/').at(-1) ?? ''), meta: { correlation_id: 'read', contract_version: CONTRACT_VERSION } });
    if (request.method === 'GET' && url.pathname.startsWith('/v1/reconstructions/')) { const incidentId = url.pathname.split('/').at(-1) ?? ''; const events = await runtimeDependencies.repositories.getEvents(tenantId!, incidentId); if (!events.length) return failure(response, 'PERMISSION_DENIED', 'Incident is not available in the authenticated tenant'); return reply(response, 200, { data: { incident_id: incidentId, events, state: await state(runtimeDependencies.repositories, tenantId!, 'memphis-fulfillment') }, meta: { correlation_id: 'read', contract_version: CONTRACT_VERSION } }); }
    return failure(response, 'VALIDATION_FAILED', 'Route not found');
    } catch (error) {
      console.error('Control Plane request failed', error);
      return failure(response, 'INTERNAL_ERROR', 'Internal server error');
    }
  });
}


