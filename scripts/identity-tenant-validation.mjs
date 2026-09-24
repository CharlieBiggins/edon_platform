import { mkdir, writeFile } from 'node:fs/promises';
import { resolve } from 'node:path';
const artifactDir = resolve(process.env.CEREBRUM_ARTIFACT_DIR ?? 'artifacts'); await mkdir(artifactDir, { recursive: true });
const issuer = process.env.OIDC_ISSUER ?? 'http://127.0.0.1:8899'; const api = process.env.CEREBRUM_API_URL ?? 'http://127.0.0.1:8787';
const token = async query => (await (await fetch(`${issuer}/token?${query}`)).json()).access_token;
const valid = await token('tenant=meridian-demo'); const expired = await token('tenant=meridian-demo&expires=-1'); const wrongAudience = await token('tenant=meridian-demo&audience=wrong-audience'); const wrongTenant = await token('tenant=other-tenant');
const stateResponse = await fetch(`${api}/v1/state/memphis-fulfillment`, { headers: { authorization: `Bearer ${valid}` } }); const stateBody = await stateResponse.json(); const expectedStateVersion = stateBody?.data?.version;
if (typeof expectedStateVersion !== 'number') throw new Error(`Current state version unavailable (${stateResponse.status})`);
const statuses = {};
const call = async (name, jwt, bindingTenant = 'meridian-demo', incidentId = 'INC-SECURITY-VALIDATION') => { const response = await fetch(`${api}/v1/events`, { method: 'POST', headers: { authorization: `Bearer ${jwt}`, 'content-type': 'application/json' }, body: JSON.stringify({ event_id: `identity-${Date.now()}-${Math.random()}`, scope_id: 'memphis-fulfillment', incident_id: incidentId, payload: {}, binding: { tenant_id: bindingTenant, actor_id: 'operator-01', correlation_id: 'identity-check', trace_id: 'identity-check', idempotency_key: `identity-${Date.now()}-${Math.random()}`, contract_version: '2026-09-24.v1', request_timestamp: new Date().toISOString(), expected_state_version: expectedStateVersion, evidence_references: [] } }) }); statuses[name] = response.status; return response.status; };
const checks = [
  { name: 'valid token accepted', passed: [200, 201].includes(await call('valid', valid)) },
  { name: 'expired token denied', passed: (await call('expired', expired)) === 403 },
  { name: 'wrong audience denied', passed: (await call('wrong_audience', wrongAudience)) === 403 },
  { name: 'wrong tenant binding denied', passed: (await call('wrong_tenant', wrongTenant)) === 403 },
];
const report = { state_version: expectedStateVersion, statuses, passed: checks.every(check => check.passed), checks }; await writeFile(`${artifactDir}/identity-tenant-isolation.json`, JSON.stringify(report, null, 2)); if (!report.passed) process.exitCode = 1;
