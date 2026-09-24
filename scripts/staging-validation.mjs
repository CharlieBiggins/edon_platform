import { mkdir, writeFile } from 'node:fs/promises';

const baseUrl = process.env.CEREBRUM_API_URL ?? 'http://127.0.0.1:8787';
const started = new Date().toISOString();
const checks = [];
async function check(name, path) {
  try { const response = await fetch(`${baseUrl}${path}`); const body = await response.json(); const passed = response.ok; checks.push({ name, passed, detail: passed ? 'endpoint ready' : String(body?.error?.code ?? 'request failed') }); } catch (error) { checks.push({ name, passed: false, detail: 'API unavailable' }); }
}
await check('process health', '/healthz');
await check('runtime readiness', '/readyz');
const binding = { tenant_id: 'meridian-demo', actor_id: 'operator-01', correlation_id: 'ci-corr-1042', trace_id: 'ci-trace-1042', idempotency_key: 'ci-idem-1042', contract_version: '2026-09-24.v1', request_timestamp: '2026-09-24T15:24:03.122Z', expected_state_version: 141, evidence_references: ['EV-2081'] };
async function post(path, payload) { const response = await fetch(`${baseUrl}${path}`, { method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify(payload) }); const data = await response.json(); checks.push({ name: `HTTP ${path}`, passed: response.ok, detail: response.ok ? 'accepted' : String(data?.error?.code ?? 'failed') }); return data?.data; }
const event = await post('/v1/events', { binding, incident_id: 'INC-1042', scope_id: 'memphis-fulfillment', payload: { capacity_units: 260 } });
await check('projected state', '/v1/state/memphis-fulfillment');
const proposal = await post('/v1/proposals', { binding });
const decision = await post('/v1/reviews', { binding, proposal_id: proposal?.proposal_id, approved: true });
await post('/v1/shadow-evaluations', { binding, proposal_id: proposal?.proposal_id });
await post('/v1/outcomes', { binding, outcome_id: 'OUT-1042', proposal_id: proposal?.proposal_id, verification_status: 'PENDING', actual_cost: 15800, commitments_protected: 3 });
await check('receipt serialization', '/v1/receipts/RCP-1042');
await check('reconstruction serialization', '/v1/reconstructions/INC-1042');
const report = { profile: process.env.CEREBRUM_RUNTIME_PROFILE ?? 'STAGING_TEST', started_at: started, finished_at: new Date().toISOString(), passed: checks.every(check => check.passed), checks };
await mkdir('artifacts', { recursive: true });
await writeFile('artifacts/staging-validation.json', JSON.stringify(report, null, 2));
if (!report.passed) process.exitCode = 1;
