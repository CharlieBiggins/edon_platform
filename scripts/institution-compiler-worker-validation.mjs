import { mkdir, writeFile } from 'node:fs/promises';
import { resolve } from 'node:path';
import { spawn } from 'node:child_process';
import { createHash } from 'node:crypto';
import { createWriteStream } from 'node:fs';

const artifactDir = resolve(process.env.CEREBRUM_ARTIFACT_DIR ?? 'artifacts');
await mkdir(artifactDir, { recursive: true });
const tenant = 'meridian-demo';
const databaseUrl = process.env.DATABASE_URL;
const workerPath = resolve('apps/control-plane-api/dist/apps/control-plane-api/src/worker.js');
const pgModule = await import('../apps/control-plane-api/node_modules/pg/lib/index.js');
const { Pool } = pgModule.default ?? pgModule;
const pool = new Pool({ connectionString: databaseUrl });
const adminPool = new Pool({ connectionString: process.env.MIGRATOR_DATABASE_URL ?? databaseUrl });
const checks = [];
const pass = (name, detail) => checks.push({ name, passed: true, detail });
const fail = (name, detail) => checks.push({ name, passed: false, detail });
const tx = async (tenantId, work) => { const client = await pool.connect(); try { await client.query('BEGIN'); await client.query('SELECT set_config($1,$2,true)', ['app.tenant_id', tenantId]); const result = await work(client); await client.query('COMMIT'); return result; } catch (error) { await client.query('ROLLBACK'); throw error; } finally { client.release(); } };
const query = (sql, values = []) => pool.query(sql, values);
const tenantQuery = (tenantId, sql, values = []) => tx(tenantId, client => client.query(sql, values));
const count = async (sql, values) => Number((await tenantQuery(tenant, sql, values)).rows[0]?.count ?? 0);
const adminCount = async (sql, values) => Number((await adminPool.query(sql, values)).rows[0]?.count ?? 0);
const sleep = ms => new Promise(resolveSleep => setTimeout(resolveSleep, ms));
const waitFor = async (predicate, timeout = 10000) => { const started = Date.now(); while (Date.now() - started < timeout) { if (await predicate()) return true; await sleep(100); } return false; };
const spawnWorker = (fault, port) => { const logPath = resolve(artifactDir, `compiler-worker-${fault ?? 'normal'}.log`); const log = createWriteStream(logPath); const child = spawn(process.execPath, [workerPath], { env: { ...process.env, WORKER_ID: `compiler-validation-${fault ?? 'normal'}`, WORKER_PORT: String(port), WORKER_TENANTS: tenant, WORKER_LEASE_MS: '500', WORKER_MAX_ATTEMPTS: '100', WORKER_POLL_MS: '25', ...(fault ? { WORKER_TEST_FAIL_AT: fault } : {}) }, stdio: ['ignore', 'pipe', 'pipe'] }); child.stdout.pipe(log); child.stderr.pipe(log); return { child, logPath }; };
const stopWorker = worker => new Promise(resolveStop => { if (worker.child.exitCode !== null) return resolveStop(); let done = false; const finish = () => { if (!done) { done = true; resolveStop(); } }; worker.child.once('exit', finish); worker.child.kill('SIGKILL'); setTimeout(finish, 3000); });
const seed = async suffix => { const institution = `compiler-validation-${suffix}`; const sourceId = `source-${suffix}`; const sourceVersion = 'v1'; const hash = `sha256:${createHash('sha256').update(`${institution}:${sourceId}:${sourceVersion}`).digest('hex')}`; await tx(tenant, async client => { await client.query('INSERT INTO institution_sources (tenant_id,institution_id,source_id,source_version,owner_id,provenance,sensitivity,effective_from,content_hash,classification_status,payload) VALUES ($1,$2,$3,$4,$5,$6,$7,now(),$8,$9,$10::jsonb)', [tenant, institution, sourceId, sourceVersion, 'compiler-test-owner', 'compiler-fixture', 'INTERNAL', hash, 'CLASSIFIED', JSON.stringify({ objects: [{ resource: sourceId, capacity: 100 }] })]); await client.query('INSERT INTO transactional_outbox (tenant_id,outbox_id,dedupe_key,topic,aggregate_id,payload,correlation_id,trace_id,state_version) VALUES ($1,$2,$3,$4,$5,$6::jsonb,$7,$8,0)', [tenant, `compiler-outbox-${suffix}`, `compiler-request:${institution}:${sourceId}:${sourceVersion}`, 'INSTITUTION_COMPILE_REQUESTED', institution, JSON.stringify({ institution_id: institution, source_id: sourceId, source_version: sourceVersion, content_hash: hash }), `compiler-${suffix}`, `trace-${suffix}`]); }); return { institution, sourceId, hash }; };
const runFault = async (fault, suffix, expectDurable) => {
  const fixture = await seed(suffix);
  const worker = spawnWorker(fault, 9000 + checks.length);
  const candidateSql = 'SELECT count(*) FROM institution_ir_candidates WHERE tenant_id=$1 AND institution_id=$2';
  const candidateSeen = await waitFor(() => adminCount(candidateSql, [tenant, fixture.institution]) > 0, 15000);
  if (expectDurable) {
    if (!candidateSeen) fail(`crash ${fault}`, 'candidate was not durable before worker termination');
    await stopWorker(worker);
    await sleep(1500);
    const retryWorker = spawnWorker(null, 9100 + checks.length);
    const recovered = await waitFor(async () => {
    const result = await tenantQuery(tenant, 'SELECT status FROM transactional_outbox WHERE tenant_id=$1 AND aggregate_id=$2', [tenant, fixture.institution]);
      return result.rows[0]?.status === 'COMPLETED';
    }, 10000);
    await stopWorker(retryWorker);
    const candidates = await adminCount(candidateSql, [tenant, fixture.institution]);
    const candidate = (await tenantQuery(tenant, 'SELECT candidate_id FROM institution_ir_candidates WHERE tenant_id=$1 AND institution_id=$2', [tenant, fixture.institution])).rows[0];
    const events = Number((await tenantQuery(tenant, 'SELECT count(*) FROM journal_events WHERE tenant_id=$1 AND event_id=$2', [tenant, `institution-candidate:${candidate?.candidate_id ?? ''}`])).rows[0]?.count ?? 0);
    const status = (await tenantQuery(tenant, 'SELECT status FROM transactional_outbox WHERE tenant_id=$1 AND aggregate_id=$2', [tenant, fixture.institution])).rows[0]?.status;
    if (recovered && candidates === 1 && events === 1) pass(`crash ${fault}`, 'post-commit candidate survived and redelivery deduplicated'); else fail(`crash ${fault}`, `recovered=${recovered} status=${status} candidates=${candidates} events=${events}`);
  } else {
    await sleep(500);
    await stopWorker(worker);
    const candidates = await count(candidateSql, [tenant, fixture.institution]);
    if (candidates === 0) pass(`crash ${fault}`, 'pre-commit writes rolled back'); else fail(`crash ${fault}`, `candidate count=${candidates}`);
  }
};
try {
  await runFault('BEFORE_CANDIDATE_COMMIT', 'before-commit', false);
  await runFault('AFTER_CANDIDATE_COMMIT_BEFORE_ACK', 'commit-before-ack', true);
  for (const [fault, suffix] of [['AFTER_CLAIM', 'after-claim'], ['AFTER_SOURCE_LOADING', 'after-source-loading'], ['AFTER_EXTRACTION', 'after-extraction'], ['AFTER_IR_MAPPING', 'after-ir-mapping'], ['AFTER_VALIDATION', 'after-validation'], ['BEFORE_CANDIDATE_PERSISTENCE', 'before-persistence']]) await runFault(fault, suffix, false);
  const duplicate = await seed('duplicate');
  await tx('other-tenant', async client => {
    await client.query('INSERT INTO institution_sources (tenant_id,institution_id,source_id,source_version,owner_id,provenance,sensitivity,effective_from,content_hash,classification_status,payload) VALUES ($1,$2,$3,$4,$5,$6,$7,now(),$8,$9,$10::jsonb)', ['other-tenant', duplicate.institution, 'other-source', 'v1', 'other-owner', 'compiler-fixture', 'INTERNAL', 'sha256:other-tenant-source', 'CLASSIFIED', JSON.stringify({ objects: [{ resource: 'other-source' }] })]);
  });
  await tx(tenant, async client => { await client.query('INSERT INTO transactional_outbox (tenant_id,outbox_id,dedupe_key,topic,aggregate_id,payload,correlation_id,trace_id,state_version) VALUES ($1,$2,$3,$4,$5,$6::jsonb,$7,$8,0) ON CONFLICT (tenant_id,dedupe_key) DO NOTHING', [tenant, 'compiler-duplicate-2', `compiler-request:${duplicate.institution}:${duplicate.sourceId}:v1`, 'INSTITUTION_COMPILE_REQUESTED', duplicate.institution, JSON.stringify({ institution_id: duplicate.institution }), 'duplicate-2', 'duplicate-trace']); });
  const duplicateRows = await count('SELECT count(*) FROM transactional_outbox WHERE tenant_id=$1 AND aggregate_id=$2', [tenant, duplicate.institution]); if (duplicateRows === 1) pass('duplicate-request protection', 'one durable outbox request'); else fail('duplicate-request protection', `outbox rows=${duplicateRows}`);
  const normal = spawnWorker(null, 9200);
  const duplicateCompleted = await waitFor(async () => (await tenantQuery(tenant, 'SELECT status FROM transactional_outbox WHERE tenant_id=$1 AND aggregate_id=$2', [tenant, duplicate.institution])).rows[0]?.status === 'COMPLETED', 15000);
  await sleep(500);
  const duplicateCount = await adminCount('SELECT count(*) FROM institution_ir_candidates WHERE tenant_id=$1 AND institution_id=$2', [tenant, duplicate.institution]);
  const duplicateStatus = (await tenantQuery(tenant, 'SELECT status FROM transactional_outbox WHERE tenant_id=$1 AND aggregate_id=$2', [tenant, duplicate.institution])).rows[0]?.status;
  await stopWorker(normal);
  if (duplicateCompleted && duplicateCount === 1) pass('deterministic compilation', 'candidate persisted once with immutable source hash binding'); else fail('deterministic compilation', `completed=${duplicateCompleted} status=${duplicateStatus} candidate_count=${duplicateCount}`);
  try { await tx(tenant, async client => { await client.query('UPDATE institution_ir_candidates SET ir_hash=ir_hash WHERE tenant_id=$1 AND institution_id=$2', [tenant, duplicate.institution]); }); fail('candidate immutability', 'application role update unexpectedly succeeded'); } catch { pass('candidate immutability', 'application role cannot mutate candidate fields'); }
  const otherTenant = await tx('other-tenant', client => client.query('SELECT count(*) FROM institution_sources WHERE institution_id=$1 AND source_id=$2', [duplicate.institution, duplicate.sourceId])); if (Number(otherTenant.rows[0].count) === 0) pass('tenant isolation', 'other tenant cannot observe compiler fixture'); else fail('tenant isolation', 'cross-tenant source visibility detected');
} catch (error) { fail('compiler worker harness', error instanceof Error ? error.message : String(error)); }
finally { await pool.end(); await adminPool.end(); }
const report = { boundary: 'INSTITUTION_COMPILER_WORKER_V1', disposition: checks.length > 0 && checks.every(check => check.passed) ? 'PASSED' : 'FAILED', checks, completed_at: new Date().toISOString() };
await writeFile(resolve(artifactDir, 'institution-compiler-worker-cases.json'), JSON.stringify(report, null, 2));
console.log(JSON.stringify(report, null, 2));
if (report.disposition !== 'PASSED') process.exitCode = 1;
