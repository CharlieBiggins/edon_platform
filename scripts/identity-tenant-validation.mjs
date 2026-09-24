import { mkdir, writeFile } from 'node:fs/promises';
import { resolve } from 'node:path';
const artifactDir = resolve(process.env.CEREBRUM_ARTIFACT_DIR ?? 'artifacts'); await mkdir(artifactDir, { recursive: true });
const issuer = process.env.OIDC_ISSUER ?? 'http://127.0.0.1:8899'; const api = process.env.CEREBRUM_API_URL ?? 'http://127.0.0.1:8787';
const token = async query => (await (await fetch(`${issuer}/token?${query}`)).json()).access_token;
const call = async (jwt, bindingTenant = 'meridian-demo') => { const response = await fetch(`${api}/v1/events`, { method: 'POST', headers: { authorization: `Bearer ${jwt}`, 'content-type': 'application/json' }, body: JSON.stringify({ event_id: `identity-${Date.now()}-${Math.random()}`, scope_id: 'memphis-fulfillment', incident_id: 'INC-1042', payload: {}, binding: { tenant_id: bindingTenant, actor_id: 'operator-01', correlation_id: 'identity-check', trace_id: 'identity-check', idempotency_key: `identity-${Date.now()}-${Math.random()}`, contract_version: '2026-09-24.v1', request_timestamp: new Date().toISOString(), expected_state_version: 141, evidence_references: [] } }) }); return response.status; };
const valid = await token('tenant=meridian-demo'); const expired = await token('tenant=meridian-demo&expires=-1'); const wrongAudience = await token('tenant=meridian-demo&audience=wrong-audience'); const wrongTenant = await token('tenant=other-tenant');
const checks = [
  { name: 'valid token accepted', passed: (await call(valid)) < 500 },
  { name: 'expired token denied', passed: (await call(expired)) === 403 },
  { name: 'wrong audience denied', passed: (await call(wrongAudience)) === 403 },
  { name: 'wrong tenant binding denied', passed: (await call(wrongTenant)) === 403 },
];
const report = { passed: checks.every(check => check.passed), checks }; await writeFile(`${artifactDir}/identity-tenant-isolation.json`, JSON.stringify(report, null, 2)); if (!report.passed) process.exitCode = 1;
