import { mkdir, writeFile } from 'node:fs/promises';
import { resolve } from 'node:path';

const baseUrl = process.env.CEREBRUM_API_URL ?? 'http://127.0.0.1:8787';
const tenant = process.env.CEREBRUM_RELEASE_TENANT ?? 'meridian-demo';
const institution = process.env.CEREBRUM_RELEASE_INSTITUTION ?? 'meridian-logistics';
const token = process.env.CEREBRUM_RELEASE_TOKEN;
const artifactDir = resolve(process.env.CEREBRUM_ARTIFACT_DIR ?? 'artifacts');
await mkdir(artifactDir, { recursive: true });
if (!token) throw new Error('CEREBRUM_RELEASE_TOKEN is required');

const checks = [];
const dbUrl = process.env.MIGRATOR_DATABASE_URL ?? process.env.DATABASE_URL;
const pgModule = await import('../apps/control-plane-api/node_modules/pg/lib/index.js');
const { Pool } = pgModule.default ?? pgModule;
const pool = new Pool({ connectionString: dbUrl });
const query = (sql, values = []) => pool.query(sql, values);
const ports = { AFTER_CAS: 8791, AFTER_JOURNAL_APPEND: 8792, AFTER_OUTBOX_ENQUEUE: 8793 };
const binding = key => ({ tenant_id: tenant, actor_id: process.env.CEREBRUM_RELEASE_ACTOR ?? 'operator-01', correlation_id: `fault-${key}`, trace_id: `trace-${key}`, idempotency_key: key, contract_version: '2026-09-24.v1', request_timestamp: new Date().toISOString(), evidence_references: [] });
const bodyFor = key => ({ institution_id: institution, expected_state: 'DRAFT', expected_version: 1, next_state: 'EXTRACTED', reason: 'fault injection qualification', binding: binding(key) });
const readSnapshot = async releaseId => {
  const release = (await query('SELECT lifecycle_state,version,manifest_hash,payload FROM institution_releases WHERE tenant_id=$1 AND release_id=$2', [tenant, releaseId])).rows[0];
  const events = (await query("SELECT event_id,event_type,payload->>'payload_hash' AS payload_hash,payload->>'previous_record_hash' AS previous_record_hash,payload FROM journal_events WHERE tenant_id=$1 AND payload->>'incident_id'=$2 ORDER BY recorded_at,event_id", [tenant, releaseId])).rows;
  const outbox = (await query('SELECT outbox_id,dedupe_key,topic,aggregate_id,payload FROM transactional_outbox WHERE tenant_id=$1 AND aggregate_id=$2 ORDER BY outbox_id', [tenant, releaseId])).rows;
  const idempotency = (await query('SELECT key,response FROM idempotency_keys WHERE tenant_id=$1 AND key LIKE $2 ORDER BY key', [tenant, `institution-release-transition:${releaseId}:%`])).rows;
  return { release, events, outbox, idempotency };
};
const start = async (port, faultPoint) => {
  const [{ createControlPlaneServer }, { PostgreSQLPlatformRepositories }, { OidcIdentityVerifier }, { DeterministicKmsProvider, KmsReceiptCustody }] = await Promise.all([
    import('../apps/control-plane-api/dist/apps/control-plane-api/src/server.js'),
    import('../apps/control-plane-api/dist/packages/platform-core/src/repositories.js'),
    import('../apps/control-plane-api/dist/packages/platform-core/src/auth.js'),
    import('../apps/control-plane-api/dist/packages/platform-core/src/receipt-custody.js'),
  ]);
  const executor = { query: (sql, values) => pool.query(sql, values), transaction: async (tenantId, work) => { const client = await pool.connect(); try { await client.query('BEGIN'); await client.query('SELECT set_config($1,$2,true)', ['app.tenant_id', tenantId]); const result = await work(client); await client.query('COMMIT'); return result; } catch (error) { await client.query('ROLLBACK'); throw error; } finally { client.release(); } } };
  const repositories = new PostgreSQLPlatformRepositories(executor);
  let fired = false;
  const injector = { failAt(point) { if (!fired && point === faultPoint) { fired = true; throw new Error(`TEST_FAULT_${point}`); } } };
  const server = createControlPlaneServer({ profile: 'STAGING_TEST', repositories, identityVerifier: new OidcIdentityVerifier(process.env.OIDC_ISSUER, process.env.OIDC_AUDIENCE, process.env.OIDC_JWKS_URL), receiptSigner: new KmsReceiptCustody(new DeterministicKmsProvider(), 'kms-test-key'), signingKeyMode: 'KMS', tenantIsolation: true, auditLogging: true, faultInjector: injector });
  await new Promise(resolve => server.listen(port, '127.0.0.1', resolve));
  return { server, stop: () => new Promise(resolve => server.close(resolve)) };
};
try {
  for (const [faultPoint, port] of Object.entries(ports)) {
    const releaseId = `REL-FAULT-${faultPoint}`;
    const idem = `fault-${faultPoint}`;
    await query("INSERT INTO institution_releases (tenant_id,institution_id,release_id,candidate_id,version,status,lifecycle_state,manifest_hash,signature_status,payload) VALUES ($1,$2,$3,$4,1,'DRAFT','DRAFT','sha256:fault-manifest','SIGNATURE_PENDING','{}'::jsonb) ON CONFLICT DO NOTHING", [tenant, institution, releaseId, `CAND-${releaseId}`]);
    const before = await readSnapshot(releaseId);
    const runtime = await start(port, faultPoint);
    const response = await fetch(`http://127.0.0.1:${port}/v1/institution-releases/${releaseId}/transition`, { method: 'POST', headers: { authorization: `Bearer ${token}`, 'content-type': 'application/json' }, body: JSON.stringify(bodyFor(idem)) });
    const responseBody = await response.json().catch(() => ({}));
    const failed = response.status >= 500;
    const afterFailure = await readSnapshot(releaseId);
    checks.push({ name: `rollback injection ${faultPoint}`, expected: '5xx with unchanged records', actual: { status: response.status, error: responseBody?.error?.code ?? null, message: responseBody?.error?.message ?? null, unchanged: JSON.stringify(before) === JSON.stringify(afterFailure) }, passed: failed && JSON.stringify(before) === JSON.stringify(afterFailure) });
    await runtime.stop();
    const retryPort = port + 100;
    const retryRuntime = await start(retryPort, null);
    const retry = await fetch(`http://127.0.0.1:${retryPort}/v1/institution-releases/${releaseId}/transition`, { method: 'POST', headers: { authorization: `Bearer ${token}`, 'content-type': 'application/json' }, body: JSON.stringify(bodyFor(idem)) });
    const retryBody = await retry.json().catch(() => ({}));
    const final = await readSnapshot(releaseId);
    checks.push({ name: `retry after ${faultPoint}`, expected: 'one successful transition', actual: { status: retry.status, error: retryBody?.error?.code ?? null, message: retryBody?.error?.message ?? null, version: final.release?.version, events: final.events.length, outbox: final.outbox.length }, passed: retry.status === 200 && Number(final.release?.version) === 2 && final.events.length === 1 && final.outbox.length === 1 });
    await retryRuntime.stop();
  }
} finally { await pool.end(); }
const report = { qualification: 'release-transition-fault-injection-v1', disposition: checks.every(check => check.passed) ? 'PASSED' : 'FAILED', checks, completed_at: new Date().toISOString() };
await writeFile(resolve(artifactDir, 'release-transition-fault-validation.json'), JSON.stringify(report, null, 2));
console.log(JSON.stringify(report, null, 2));
if (report.disposition !== 'PASSED') {
  for (const check of checks.filter(check => !check.passed)) console.error(`FAILED: ${check.name}`, JSON.stringify(check.actual));
  process.exit(1);
}
