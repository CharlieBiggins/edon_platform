import { mkdir, writeFile } from 'node:fs/promises';
import { resolve } from 'node:path';

const baseUrl = process.env.CEREBRUM_API_URL ?? 'http://127.0.0.1:8787';
const authorization = process.env.CEREBRUM_AUTH_TOKEN ? { authorization: `Bearer ${process.env.CEREBRUM_AUTH_TOKEN}` } : {};
const durabilityAuthorization = process.env.CEREBRUM_DURABILITY_TOKEN ? { authorization: `Bearer ${process.env.CEREBRUM_DURABILITY_TOKEN}` } : authorization;
const artifactDir = resolve(process.env.CEREBRUM_ARTIFACT_DIR ?? 'artifacts');
await mkdir(artifactDir, { recursive: true });
const started = new Date().toISOString();
const checks = [];
async function check(name, path, headers = authorization) {
  try { const response = await fetch(`${baseUrl}${path}`, { headers }); const body = await response.json(); const passed = response.ok; checks.push({ name, passed, detail: passed ? 'endpoint ready' : String(body?.error?.code ?? 'request failed') }); return body?.data; } catch (error) { checks.push({ name, passed: false, detail: 'API unavailable' }); return undefined; }
}
await check('process health', '/healthz');
await check('runtime readiness', '/readyz');
const binding = { tenant_id: 'meridian-demo', actor_id: 'operator-01', correlation_id: 'ci-corr-1042', trace_id: 'ci-trace-1042', idempotency_key: 'ci-idem-1042', contract_version: '2026-09-24.v1', request_timestamp: '2026-09-24T15:24:03.122Z', expected_state_version: 141, evidence_references: ['EV-2081'] };
let postSequence = 0;
async function post(path, payload) {
  postSequence += 1;
  const operation = path.replace(/^\/v1\//, '').replace(/[^a-z0-9]+/gi, '-');
  const requestBinding = { ...(payload.binding ?? binding), idempotency_key: `ci-${operation}-${postSequence}` };
  const response = await fetch(`${baseUrl}${path}`, { method: 'POST', headers: { 'content-type': 'application/json', ...authorization }, body: JSON.stringify({ ...payload, binding: requestBinding }) });
  const data = await response.json();
  checks.push({ name: `HTTP ${path}`, passed: response.ok, detail: response.ok ? 'accepted' : `${String(data?.error?.code ?? 'failed')}: ${String(data?.error?.message ?? '')}`.trim() });
  return data?.data;
}
function assertValue(name, condition, detail) { checks.push({ name, passed: Boolean(condition), detail }); }
const event = await post('/v1/events', { binding, incident_id: 'INC-1042', scope_id: 'memphis-fulfillment', payload: { capacity_units: 260 } });
const projectedState = await check('projected state', '/v1/state/memphis-fulfillment');
if (typeof projectedState?.version === 'number') binding.expected_state_version = projectedState.version;
const proposal = await post('/v1/proposals', { binding });
assertValue('proposal created', Boolean(proposal?.proposal_id), 'proposal identifier returned');
const decision = await post('/v1/reviews', { binding, proposal_id: proposal?.proposal_id, proposal_hash: proposal?.proposal_hash, context_hash: proposal?.context?.state_hash, approved: true });
assertValue('Kernel reevaluation', decision?.disposition === 'DENY' || decision?.disposition === 'ALLOW', `disposition=${decision?.disposition ?? 'missing'}`);
await post('/v1/shadow-evaluations', { binding, proposal_id: proposal?.proposal_id });
await post('/v1/outcomes', { binding, outcome_id: 'OUT-1042', proposal_id: proposal?.proposal_id, verification_status: 'PENDING', actual_cost: 15800, commitments_protected: 3 });
const receiptResponse = await fetch(`${baseUrl}/v1/receipts/RCP-${proposal?.proposal_id}`, { headers: authorization }); const receiptBody = await receiptResponse.json(); assertValue('receipt serialization', receiptResponse.ok && Boolean(receiptBody?.data), receiptResponse.ok ? (receiptBody?.data ? 'receipt survives HTTP serialization' : 'receipt response contained no data') : `HTTP ${receiptResponse.status} ${String(receiptBody?.error?.code ?? 'request failed')}`);
await check('reconstruction serialization', '/v1/reconstructions/INC-1042', durabilityAuthorization);
const report = { profile: process.env.CEREBRUM_RUNTIME_PROFILE ?? 'STAGING_TEST', started_at: started, finished_at: new Date().toISOString(), passed: checks.every(check => check.passed), checks };
await writeFile(`${artifactDir}/staging-validation.json`, JSON.stringify(report, null, 2));
if (!report.passed) process.exitCode = 1;
