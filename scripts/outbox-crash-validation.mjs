import { mkdir, writeFile } from 'node:fs/promises';
import { resolve } from 'node:path';
import { spawn } from 'node:child_process';
import { createRequire } from 'node:module';

const artifactDir = resolve(process.env.ARTIFACT_DIR ?? process.env.CEREBRUM_ARTIFACT_DIR ?? 'artifacts');
await mkdir(artifactDir, { recursive: true });
const tenant = process.env.OUTBOX_HARNESS_TENANT ?? 'worker-crash-test';
const databaseUrl = process.env.DATABASE_URL;
if (!databaseUrl) throw new Error('DATABASE_URL is required');
const { Pool } = createRequire(import.meta.url)('../command-center/node_modules/pg');
const pool = new Pool({ connectionString: databaseUrl });
const checks = [];
const sql = async (text, values = [], tenantId = tenant) => {
  const client = await pool.connect();
  try { await client.query('BEGIN'); await client.query('SELECT set_config($1,$2,true)', ['app.tenant_id', tenantId]); const result = await client.query(text, values); await client.query('COMMIT'); return result; }
  catch (error) { try { await client.query('ROLLBACK'); } catch {} throw error; } finally { client.release(); }
};
const harnessPort = process.env.OUTBOX_HARNESS_PORT ?? '8790';
const workerEnv = { ...process.env, WORKER_PORT: harnessPort, WORKER_ID: `crash-harness-${process.pid}`, WORKER_LEASE_MS: '1000', WORKER_MAX_ATTEMPTS: '3', WORKER_TENANTS: tenant, WORKER_ACTOR_ID: 'outbox-worker-ci', WORKER_PAUSE_BEFORE_HANDLE_MS: '0', WORKER_PAUSE_BEFORE_COMPLETE_MS: '0' };
const startWorker = (pause = '0') => { const child = spawn(process.execPath, ['apps/control-plane-api/dist/apps/control-plane-api/src/worker.js'], { env: { ...workerEnv, WORKER_PAUSE_BEFORE_HANDLE_MS: pause }, stdio: ['ignore', 'pipe', 'pipe'] }); child.stdout.pipe(process.stdout); child.stderr.pipe(process.stderr); return child; };
const waitReady = async () => { for (let attempt = 0; attempt < 40; attempt += 1) { try { const response = await fetch(`http://127.0.0.1:${harnessPort}/readyz`); if (response.ok) return; } catch {} await new Promise(resolve => setTimeout(resolve, 100)); } throw new Error('worker readiness timeout'); };
const insert = async (id, topic = 'TEST_RECOVERY') => { await sql('INSERT INTO transactional_outbox (tenant_id,outbox_id,dedupe_key,topic,aggregate_id,payload,correlation_id,trace_id,state_version) VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9)', [tenant, id, `harness:${id}`, topic, 'INC-OUTBOX-CRASH', JSON.stringify({ scope_id: 'memphis-fulfillment', state_version: 141 }), `corr-${id}`, `trace-${id}`, 141]); };
const status = async id => (await sql('SELECT status,attempts,worker_id,lease_expires_at FROM transactional_outbox WHERE tenant_id=$1 AND outbox_id=$2', [tenant, id])).rows[0];
const rolledBack = 'crash-rolled-back';
const client = await pool.connect();
try { await client.query('BEGIN'); await client.query("SELECT set_config($1,$2,true)", ['app.tenant_id', tenant]); await client.query('INSERT INTO transactional_outbox (tenant_id,outbox_id,dedupe_key,topic,aggregate_id,payload,correlation_id,trace_id) VALUES ($1,$2,$3,$4,$5,$6,$7,$8)', [tenant, rolledBack, `harness:${rolledBack}`, 'TEST_ROLLBACK', 'INC-OUTBOX-CRASH', '{}', 'corr-rollback', 'trace-rollback']); await client.query('ROLLBACK'); } finally { client.release(); }
checks.push({ name: 'rollback leaves no deliverable message', passed: (await sql('SELECT count(*)::int AS count FROM transactional_outbox WHERE tenant_id=$1 AND outbox_id=$2', [tenant, rolledBack])).rows[0].count === 0 });
const abandoned = `crash-abandoned-${Date.now()}`; await insert(abandoned); let worker = startWorker('10000'); await waitReady(); for (let i = 0; i < 30; i += 1) { const row = await status(abandoned); if (row?.status === 'PROCESSING') break; await new Promise(resolve => setTimeout(resolve, 100)); } worker.kill('SIGTERM'); await new Promise(resolve => setTimeout(resolve, 1400)); worker = startWorker(); await waitReady(); for (let i = 0; i < 40; i += 1) { if ((await status(abandoned))?.status === 'COMPLETED') break; await new Promise(resolve => setTimeout(resolve, 100)); }
checks.push({ name: 'abandoned claim resumes after lease expiry', passed: (await status(abandoned))?.status === 'COMPLETED' });
const duplicate = `crash-duplicate-${Date.now()}`; await insert(duplicate); const duplicateAgain = await sql('INSERT INTO transactional_outbox (tenant_id,outbox_id,dedupe_key,topic,aggregate_id,payload,correlation_id,trace_id) VALUES ($1,$2,$3,$4,$5,$6,$7,$8) ON CONFLICT (tenant_id,dedupe_key) DO NOTHING RETURNING outbox_id', [tenant, `${duplicate}-second`, `harness:${duplicate}`, 'TEST_RECOVERY', 'INC-OUTBOX-CRASH', '{}', 'corr-duplicate', 'trace-duplicate']); checks.push({ name: 'duplicate delivery is deduplicated', passed: duplicateAgain.rows.length === 0 });
const dead = `crash-dead-${Date.now()}`; await insert(dead, 'TEST_PERMANENT_FAILURE'); for (let i = 0; i < 60; i += 1) { if ((await status(dead))?.status === 'DEAD_LETTER') break; await new Promise(resolve => setTimeout(resolve, 250)); } checks.push({ name: 'exhausted failure reaches dead letter', passed: (await status(dead))?.status === 'DEAD_LETTER' });
const crossTenant = (await sql('SELECT count(*)::int AS count FROM transactional_outbox', [], 'other-tenant')).rows[0].count; checks.push({ name: 'tenant isolation hides other messages', passed: crossTenant === 0 });
worker.kill('SIGTERM'); await pool.end(); const report = { passed: checks.every(check => check.passed), semantics: 'at-least-once', checks }; await writeFile(resolve(artifactDir, 'outbox-crash-validation.json'), JSON.stringify(report, null, 2)); if (!report.passed) process.exitCode = 1;
