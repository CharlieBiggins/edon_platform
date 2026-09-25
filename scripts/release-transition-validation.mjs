import { mkdir, writeFile } from 'node:fs/promises';
import { resolve } from 'node:path';
import { createHash } from 'node:crypto';

const baseUrl = process.env.CEREBRUM_API_URL ?? 'http://127.0.0.1:8787';
const token = process.env.CEREBRUM_RELEASE_TOKEN ?? process.env.CEREBRUM_AUTH_TOKEN;
const tenant = process.env.CEREBRUM_RELEASE_TENANT ?? 'meridian-demo';
const actor = process.env.CEREBRUM_RELEASE_ACTOR ?? 'operator-01';
const institution = process.env.CEREBRUM_RELEASE_INSTITUTION ?? 'meridian-logistics';
const releaseId = process.env.CEREBRUM_RELEASE_ID;
const artifactDir = resolve(process.env.CEREBRUM_ARTIFACT_DIR ?? 'artifacts');
await mkdir(artifactDir, { recursive: true });
if (!token || !releaseId) throw new Error('CEREBRUM_RELEASE_TOKEN and CEREBRUM_RELEASE_ID are required');
const startedAt = new Date().toISOString();

const checks = [];
const hash = value => createHash('sha256').update(JSON.stringify(value ?? null)).digest('hex');
const request = async (name, method, path, body, expected, authToken = token) => {
  const response = await fetch(`${baseUrl}${path}`, { method, headers: { authorization: `Bearer ${authToken}`, 'content-type': 'application/json' }, body: body ? JSON.stringify(body) : undefined });
  const data = await response.json().catch(() => ({}));
  const passed = Array.isArray(expected) ? expected.includes(response.status) : response.status === expected;
  checks.push({ name, expected_status: expected, actual_status: response.status, passed, error_code: data?.error?.code ?? null });
  return { response, data };
};
const binding = idempotencyKey => ({ tenant_id: tenant, actor_id: actor, correlation_id: `release-validation-${idempotencyKey}`, trace_id: `trace-${idempotencyKey}`, idempotency_key: idempotencyKey, contract_version: '2026-09-24.v1', request_timestamp: new Date().toISOString(), evidence_references: [] });

const initial = await request('read release baseline', 'GET', `/v1/institution-releases/${encodeURIComponent(releaseId)}`, null, 200);
if (!initial.data?.data) throw new Error('Release baseline unavailable');
const release = initial.data.data;
const expectedState = process.env.CEREBRUM_RELEASE_EXPECTED_STATE ?? release.lifecycle_state;
const expectedVersion = Number(process.env.CEREBRUM_RELEASE_EXPECTED_VERSION ?? release.version);
const nextState = process.env.CEREBRUM_RELEASE_NEXT_STATE ?? (expectedState === 'DRAFT' ? 'EXTRACTED' : 'REJECTED');
const makeBody = key => ({ institution_id: institution, expected_state: expectedState, expected_version: expectedVersion, next_state: nextState, reason: 'staging acceptance', binding: binding(key) });

const noAuth = await fetch(`${baseUrl}/v1/institution-releases/${encodeURIComponent(releaseId)}`).then(async response => ({ status: response.status, body: await response.json().catch(() => ({})) }));
checks.push({ name: 'missing token is rejected', expected_status: 401, actual_status: noAuth.status, passed: noAuth.status === 401, error_code: noAuth.body?.error?.code ?? null });
const foreignBody = makeBody('foreign-tenant');
foreignBody.binding = { ...foreignBody.binding, tenant_id: 'other-tenant' };
const foreign = await request('tenant substitution is rejected', 'POST', `/v1/institution-releases/${encodeURIComponent(releaseId)}/transition`, foreignBody, 403);

const [first, second] = await Promise.all([
  request('concurrent transition A', 'POST', `/v1/institution-releases/${encodeURIComponent(releaseId)}/transition`, makeBody('transition-a'), [200, 409, 422]),
  request('concurrent transition B', 'POST', `/v1/institution-releases/${encodeURIComponent(releaseId)}/transition`, makeBody('transition-b'), [200, 409, 422]),
]);
const winner = first.response.status === 200 ? first : second;
const loser = first.response.status === 200 ? second : first;
checks.push({ name: 'one concurrent transition wins', expected: 'one 200 and one conflict', actual: [first.response.status, second.response.status], passed: winner.response.status === 200 && [409, 422].includes(loser.response.status) });

const winnerKey = winner.data?.data?.idempotency_key ?? 'transition-a';
const retry = await request('idempotent retry returns original result', 'POST', `/v1/institution-releases/${encodeURIComponent(releaseId)}/transition`, makeBody(winnerKey), 200);
checks.push({ name: 'idempotent response matches original', expected: hash(winner.data?.data), actual: hash(retry.data?.data), passed: JSON.stringify(winner.data?.data) === JSON.stringify(retry.data?.data), response_match: JSON.stringify(winner.data?.data) === JSON.stringify(retry.data?.data), original: winner.data?.data ?? null, retry: retry.data?.data ?? null });

const after = await request('read release after transition', 'GET', `/v1/institution-releases/${encodeURIComponent(releaseId)}`, null, 200);
checks.push({ name: 'one release version advancement', expected: expectedVersion + 1, actual: after.data?.data?.version, passed: Number(after.data?.data?.version) === expectedVersion + 1 });
const reconstruction = await request('reconstruct transition history', 'GET', `/v1/reconstructions/${encodeURIComponent(releaseId)}`, null, 200, process.env.CEREBRUM_DURABILITY_TOKEN ?? token);
const events = reconstruction.data?.data?.events ?? [];
checks.push({ name: 'one transition journal event', expected: 1, actual: events.filter(event => event.event_type === 'INSTITUTION_RELEASE_TRANSITIONED').length, passed: events.filter(event => event.event_type === 'INSTITUTION_RELEASE_TRANSITIONED').length === 1 });
checks.push({ name: 'journal chain is linked', expected: 'valid', actual: events.every((event, index) => index === 0 || event.previous_record_hash === events[index - 1].payload_hash), passed: events.every((event, index) => index === 0 || event.previous_record_hash === events[index - 1].payload_hash) });

const passed = checks.every(check => check.passed);
const report = {
  qualification: 'release-transition-acceptance-v1',
  disposition: passed ? 'QUALIFIED' : 'FAILED',
  commit_sha: process.env.GITHUB_SHA ?? 'local',
  tenant, institution, release_id: releaseId,
  migration_versions: process.env.CEREBRUM_MIGRATION_VERSIONS?.split(',').filter(Boolean) ?? [],
  postgres_version: process.env.CEREBRUM_POSTGRES_VERSION ?? 'unknown',
  started_at: startedAt, completed_at: new Date().toISOString(),
  expected_results: checks.map(check => ({ name: check.name, expected_status: check.expected_status ?? check.expected })),
  actual_results: checks.map(check => ({ name: check.name, actual_status: check.actual_status ?? check.actual, passed: check.passed })),
  checks,
  canonical_hashes: { baseline_release: hash(release), final_release: hash(after.data?.data), reconstruction: hash(reconstruction.data?.data) },
  passed,
};
await writeFile(resolve(artifactDir, 'release-transition-validation.json'), JSON.stringify(report, null, 2));
if (!report.passed) process.exitCode = 1;
