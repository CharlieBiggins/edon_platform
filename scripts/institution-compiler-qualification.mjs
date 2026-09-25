import { createHash } from 'node:crypto';
import { mkdir, writeFile } from 'node:fs/promises';
import { resolve } from 'node:path';

const artifactDir = resolve(process.env.CEREBRUM_ARTIFACT_DIR ?? 'artifacts');
await mkdir(artifactDir, { recursive: true });
const phase = process.env.CEREBRUM_COMPILER_PHASE;
const tenant = process.env.CEREBRUM_COMPILER_TENANT;
const institution = process.env.CEREBRUM_COMPILER_INSTITUTION;
const databaseUrl = process.env.DATABASE_URL ?? process.env.MIGRATOR_DATABASE_URL;
const checks = [];
const fail = (name, detail) => checks.push({ name, passed: false, detail });
const pass = (name, detail) => checks.push({ name, passed: true, detail });
const requiredCaseNames = ['atomic submission', 'duplicate-request protection', 'crash after claim', 'crash after source loading', 'crash after extraction', 'crash after IR mapping', 'crash after validation', 'crash before candidate persistence', 'crash after candidate persistence', 'deterministic compilation', 'source-binding enforcement', 'candidate immutability', 'tenant isolation', 'restart equality', 'backup/restore equality'];
let suppliedCases = {};
try { suppliedCases = JSON.parse(process.env.CEREBRUM_COMPILER_REQUIRED_CASES ?? '{}'); } catch { fail('required-case manifest', 'CEREBRUM_COMPILER_REQUIRED_CASES is not valid JSON'); }
for (const name of requiredCaseNames) suppliedCases[name] === true ? pass(name, 'reported by PostgreSQL qualification harness') : fail(name, 'required case missing or failed');
if (!phase || !['baseline', 'restart', 'restore'].includes(phase)) fail('phase binding', 'CEREBRUM_COMPILER_PHASE must be baseline, restart or restore');
if (!tenant || !institution) fail('scope binding', 'CEREBRUM_COMPILER_TENANT and CEREBRUM_COMPILER_INSTITUTION are required');
if (!databaseUrl) fail('database binding', 'DATABASE_URL or MIGRATOR_DATABASE_URL is required');

const stable = value => {
  if (Array.isArray(value)) return `[${value.map(stable).join(',')}]`;
  if (value && typeof value === 'object') return `{${Object.keys(value).sort().map(key => `${JSON.stringify(key)}:${stable(value[key])}`).join(',')}}`;
  return JSON.stringify(value);
};
const digest = value => `sha256:${createHash('sha256').update(stable(value)).digest('hex')}`;
let pool;
let snapshot = null;
try {
  const pgModule = await import('../apps/control-plane-api/node_modules/pg/lib/index.js');
  const { Pool } = pgModule.default ?? pgModule;
  pool = new Pool({ connectionString: databaseUrl });
  const query = (sql, values = []) => pool.query(sql, values);
  const sources = (await query('SELECT tenant_id,institution_id,source_id,source_version,content_hash,classification_status,payload FROM institution_sources WHERE tenant_id=$1 AND institution_id=$2 ORDER BY source_id,source_version', [tenant, institution])).rows;
  const candidates = (await query('SELECT tenant_id,institution_id,candidate_id,version,ir_hash,compiler_version,input_source_hashes,validation_findings,control_graph_diff,status,payload FROM institution_ir_candidates WHERE tenant_id=$1 AND institution_id=$2 ORDER BY candidate_id', [tenant, institution])).rows;
  const outbox = (await query("SELECT outbox_id,dedupe_key,topic,aggregate_id,payload,status,attempts FROM transactional_outbox WHERE tenant_id=$1 AND aggregate_id=$2 ORDER BY outbox_id", [tenant, institution])).rows;
  snapshot = { tenant, institution, sources, candidates, outbox };
  if (sources.length) pass('tenant-scoped source loading', `${sources.length} source versions`); else fail('tenant-scoped source loading', 'no source versions persisted');
  if (candidates.length) pass('candidate persistence', `${candidates.length} candidate records`); else fail('candidate persistence', 'no candidate records persisted');
  if (outbox.some(row => row.topic === 'INSTITUTION_COMPILE_REQUESTED')) pass('durable compilation request', 'compile outbox message present'); else fail('durable compilation request', 'compile outbox message missing');
  const candidateHashes = new Set(candidates.map(row => row.ir_hash));
  if (candidateHashes.size === candidates.length) pass('candidate deduplication', 'candidate hashes are unique'); else fail('candidate deduplication', 'duplicate candidate hash detected');
  for (const candidate of candidates) {
    const expected = new Set(sources.map(source => `${source.source_id}@${source.source_version}:${source.content_hash}`));
    const actual = new Set(Array.isArray(candidate.input_source_hashes) ? candidate.input_source_hashes : []);
    if ([...actual].every(hash => expected.has(hash))) pass(`source binding ${candidate.candidate_id}`, 'all hashes resolve to immutable source versions'); else fail(`source binding ${candidate.candidate_id}`, 'candidate references missing or modified source content');
  }
  const canonicalDigest = digest(snapshot);
  const digestFile = resolve(artifactDir, 'institution-compiler-canonical-digest.json');
  if (phase === 'baseline') await writeFile(digestFile, JSON.stringify({ phase, canonical_digest: canonicalDigest }, null, 2));
  else {
    const expected = JSON.parse(await import('node:fs/promises').then(fs => fs.readFile(digestFile, 'utf8'))).canonical_digest;
    if (expected === canonicalDigest) pass(`${phase} equality`, canonicalDigest); else fail(`${phase} equality`, `expected ${expected}, received ${canonicalDigest}`);
  }
} catch (error) { fail('qualification runner', error instanceof Error ? error.message : String(error)); }
finally { if (pool) await pool.end(); }

const required = ['phase binding', 'scope binding', 'database binding', 'tenant-scoped source loading', 'candidate persistence', 'durable compilation request', 'candidate deduplication', ...requiredCaseNames];
for (const name of required) if (!checks.some(check => check.name === name)) fail(name, 'required case did not run');
const report = { boundary: 'INSTITUTION_COMPILER_WORKER_V1', disposition: checks.length > 0 && checks.every(check => check.passed) ? 'QUALIFIED' : 'FAILED', phase, tenant, institution, canonical_digest: snapshot ? digest(snapshot) : null, required_cases: Object.fromEntries(checks.map(check => [check.name, check.passed ? 'PASSED' : 'FAILED'])), checks, completed_at: new Date().toISOString() };
await writeFile(resolve(artifactDir, 'institution-compiler-qualification.json'), JSON.stringify(report, null, 2));
console.log(JSON.stringify(report, null, 2));
if (report.disposition !== 'QUALIFIED') process.exitCode = 1;
