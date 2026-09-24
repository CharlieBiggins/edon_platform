import { mkdir, writeFile } from 'node:fs/promises';
import { resolve } from 'node:path';
const artifactDir = resolve(process.env.CEREBRUM_ARTIFACT_DIR ?? 'artifacts');
const issuer = process.env.OIDC_ISSUER ?? 'http://127.0.0.1:8899';
const api = process.env.CEREBRUM_API_URL ?? 'http://127.0.0.1:8787';
const report = { expected_tenant: 'meridian-demo', expected_incident: 'INC-1042', expected_reconstruction_role: 'auditor', cases: [], passed: false };
await mkdir(artifactDir, { recursive: true });
const token = async query => (await (await fetch(`${issuer}/token?${query}`)).json()).access_token;
const sanitized = body => body?.error ? { code: String(body.error.code ?? 'API_ERROR'), message: String(body.error.message ?? '').slice(0, 300) } : { body: String(JSON.stringify(body ?? {})).slice(0, 500) };
async function requestCase(name, jwt, expectedStatus, role, tenant, method = 'GET', path = '/v1/reconstructions/INC-1042') {
  const response = await fetch(`${api}${path}`, { method, headers: jwt ? { authorization: `Bearer ${jwt}` } : {} });
  const body = await response.json().catch(() => ({}));
  const result = { name, method, path, expected_status: expectedStatus, actual_status: response.status, error: sanitized(body), response_body: sanitized(body), expected_actor_role: role, expected_tenant: tenant, passed: response.status === expectedStatus };
  report.cases.push(result); console.log(`${result.passed ? 'PASS' : 'FAIL'} ${name}: expected ${expectedStatus}, received ${response.status}`); return result;
}
try {
  const validAudit = await token('tenant=meridian-demo&role=auditor'); const operator = await token('tenant=meridian-demo&role=operator'); const otherAudit = await token('tenant=other-tenant&role=auditor'); const expired = await token('tenant=meridian-demo&role=auditor&expires=-1'); const inactive = await token('tenant=meridian-demo&role=auditor&active=false'); const wrongAudience = await token('tenant=meridian-demo&role=auditor&audience=wrong-audience'); const wrongIssuer = await token('tenant=meridian-demo&role=auditor&issuer=http://wrong-issuer');
  await requestCase('missing token', undefined, 401, 'none', 'meridian-demo'); await requestCase('malformed token', 'not-a-jwt', 401, 'none', 'meridian-demo'); await requestCase('wrong issuer', wrongIssuer, 401, 'auditor', 'meridian-demo'); await requestCase('wrong audience', wrongAudience, 401, 'auditor', 'meridian-demo'); await requestCase('expired token', expired, 401, 'auditor', 'meridian-demo'); await requestCase('inactive actor', inactive, 403, 'auditor', 'meridian-demo'); await requestCase('valid actor and matching tenant', validAudit, 200, 'auditor', 'meridian-demo'); await requestCase('valid actor from another tenant', otherAudit, 403, 'auditor', 'other-tenant'); await requestCase('operator without reconstruction permission', operator, 403, 'operator', 'meridian-demo'); await requestCase('authorized audit reconstruction reader', validAudit, 200, 'auditor', 'meridian-demo');
  report.passed = report.cases.every(item => item.passed); await writeFile(`${artifactDir}/identity-tenant-validation.json`, JSON.stringify(report, null, 2));
  if (!report.passed) { console.error('Identity validation failed:'); for (const item of report.cases.filter(item => !item.passed)) console.error(`FAIL ${item.name}: expected ${item.expected_status}, received ${item.actual_status} (${item.error.code ?? item.error.body})`); process.exitCode = 1; }
} catch (error) { report.unexpected_error = error instanceof Error ? error.stack : String(error); await writeFile(`${artifactDir}/identity-tenant-validation.json`, JSON.stringify(report, null, 2)); console.error('Unexpected identity validation error:', report.unexpected_error); process.exitCode = 1; }
