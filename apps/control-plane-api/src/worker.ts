import { createServer, type IncomingMessage, type ServerResponse } from 'node:http';
import { createHash } from 'node:crypto';
import { PostgreSQLPlatformRepositories, type InstitutionCandidateRecord, type OutboxMessage } from '../../../packages/platform-core/src/repositories.js';
import { DurableOutboxWorker } from '../../../packages/platform-core/src/outbox-worker.js';
import { requireRuntimeEnvironment } from './runtime.js';
import { AwsKmsProvider, canonicalize, DeterministicKmsProvider, KmsReceiptCustody } from '../../../packages/platform-core/src/receipt-custody.js';

const config = requireRuntimeEnvironment(process.env);
const tenants = (process.env.WORKER_TENANTS ?? 'meridian-demo').split(',').map(value => value.trim()).filter(Boolean);
const workerId = process.env.WORKER_ID ?? `worker-${process.pid}`;
const pollMs = Math.max(50, Number(process.env.WORKER_POLL_MS ?? 250));
const leaseMs = Math.max(1000, Number(process.env.WORKER_LEASE_MS ?? 30000));
const maxAttempts = Math.max(1, Number(process.env.WORKER_MAX_ATTEMPTS ?? 5));
const workerPort = Number(process.env.WORKER_PORT ?? config.port + 1);
if (!process.env.WORKER_ACTOR_ID) throw new Error('WORKER_ACTOR_ID is required for the server-only worker');
if (process.env.WORKER_ACTOR_ID === 'operator-01' || process.env.WORKER_ACTOR_TYPE === 'HUMAN') throw new Error('Workers require a distinct service identity');

type PgClient = { query: <T = unknown>(text: string, values?: unknown[]) => Promise<{ rows: T[] }>; release: () => void };
type PgPool = { query: <T = unknown>(text: string, values?: unknown[]) => Promise<{ rows: T[] }>; connect: () => Promise<PgClient>; end: () => Promise<void> };
const loadPg = new Function('specifier', 'return import(specifier)') as (specifier: string) => Promise<{ Pool: new (options: { connectionString: string; max?: number }) => PgPool }>;
const pg = await loadPg('pg');
const pool = new pg.Pool({ connectionString: config.databaseUrl, max: Math.max(4, tenants.length * 2) });
const executor = {
  query: <T = unknown>(text: string, values?: unknown[]) => pool.query<T>(text, values),
  transaction: async <T>(tenantId: string, work: (db: PgClient) => Promise<T>) => {
    const client = await pool.connect();
    try { await client.query('BEGIN'); await client.query('SELECT set_config($1,$2,true)', ['app.tenant_id', tenantId]); const result = await work(client); await client.query('COMMIT'); return result; }
    catch (error) { try { await client.query('ROLLBACK'); } catch {} throw error; }
    finally { client.release(); }
  },
};
const repositories = new PostgreSQLPlatformRepositories(executor);
const receiptSigner = new KmsReceiptCustody(config.profile === 'STAGING_TEST' ? new DeterministicKmsProvider() : new AwsKmsProvider(), config.profile === 'STAGING_TEST' ? 'kms-test-key' : (config.kmsKeyId ?? ''));
const metrics = new Map<string, Awaited<ReturnType<typeof repositories.getOutboxMetrics>>>();
const verify = async (message: OutboxMessage) => {
  if (!tenants.includes(message.tenant_id)) throw new Error('WORKER_TENANT_NOT_PERMITTED');
  if (message.state_version !== undefined && message.state_version > 0) {
    const state = await repositories.transaction(message.tenant_id, scoped => scoped.getState(message.tenant_id, String(message.payload.scope_id ?? 'memphis-fulfillment')));
    if (state && state.version !== message.state_version) throw new Error('STATE_VERSION_BINDING_MISMATCH');
  }
};
// Shadow handlers are deliberately side-effect-free and deduplicated by durable outbox keys.
const pause = async (name: string) => { const delay = Number(process.env[name] ?? 0); if (delay > 0) await new Promise(resolve => setTimeout(resolve, delay)); };
const digest = (value: unknown) => `sha256:${createHash('sha256').update(canonicalize(value)).digest('hex')}`;
const compileInstitution = async (message: OutboxMessage) => {
  const institutionId = String(message.payload.institution_id ?? message.aggregate_id);
  const sources = await repositories.transaction(message.tenant_id, scoped => scoped.listInstitutionSources(message.tenant_id, institutionId));
  const ordered = sources.slice().sort((a, b) => `${a.source_id}:${a.source_version}`.localeCompare(`${b.source_id}:${b.source_version}`));
  const sourceHashes = ordered.map(source => `${source.source_id}@${source.source_version}:${source.content_hash}`);
  const findings: Array<Record<string, unknown>> = [];
  for (const source of ordered) {
    if (!source.content_hash || !source.source_version || !source.provenance || !source.owner_id) findings.push({ code: 'SOURCE_METADATA_INCOMPLETE', source_id: source.source_id, source_version: source.source_version });
    if (source.classification_status === 'REJECTED') findings.push({ code: 'SOURCE_REJECTED', source_id: source.source_id, source_version: source.source_version });
  }
  const extracted = ordered.map(source => ({ source_id: source.source_id, source_version: source.source_version, content_hash: source.content_hash, objects: source.payload.objects ?? source.payload }));
  const ir = { institution_id: institutionId, sources: extracted, compiler_version: 'institution-compiler-v1', stages: ['EXTRACTION', 'IR_MAPPING', 'VALIDATION'] };
  const graphDiff = { added: extracted.flatMap(item => Array.isArray(item.objects) ? item.objects : []), changed: [], removed: [] };
  const irHash = digest(ir);
  const candidateId = `candidate-${irHash.slice(-16)}`;
  const candidate: InstitutionCandidateRecord = { tenant_id: message.tenant_id, institution_id: institutionId, candidate_id: candidateId, version: '1', ir_hash: irHash, compiler_version: 'institution-compiler-v1', input_source_hashes: sourceHashes, validation_findings: findings, control_graph_diff: graphDiff, status: findings.length ? 'DRAFT' : 'VALIDATED', payload: { ir, source_count: ordered.length, deterministic: true, correlation_id: message.correlation_id, trace_id: message.trace_id } };
  await repositories.transaction(message.tenant_id, scoped => scoped.createInstitutionCandidate(candidate));
};
const handle = async (message: OutboxMessage) => { if (message.topic === 'TEST_PERMANENT_FAILURE') throw new Error('TEST_PERMANENT_FAILURE'); if (message.topic === 'INSTITUTION_SOURCE_CHANGED' || message.topic === 'INSTITUTION_COMPILE_REQUESTED') await compileInstitution(message); if (message.topic === 'RECEIPT_SIGN') { const receiptId = String(message.payload.receipt_id ?? ''); const receipt = await repositories.transaction(message.tenant_id, scoped => scoped.getReceipt(message.tenant_id, receiptId)); if (!receipt) throw new Error('RECEIPT_NOT_FOUND'); const existing = await repositories.transaction(message.tenant_id, scoped => scoped.getReceiptCustody(message.tenant_id, receiptId)); if (!existing) { const claimed = await repositories.transaction(message.tenant_id, scoped => scoped.claimReceiptSigning(message.tenant_id, receiptId, workerId, leaseMs)); if (claimed) { const signature = await receiptSigner.sign(canonicalize(receipt)); await repositories.transaction(message.tenant_id, scoped => scoped.putReceiptCustody({ tenant_id: message.tenant_id, receipt_id: receiptId, status: 'SIGNED', ...signature })); await repositories.transaction(message.tenant_id, scoped => scoped.completeReceiptSigning(message.tenant_id, receiptId)); } } } await pause('WORKER_PAUSE_BEFORE_COMPLETE_MS'); /* external calls belong here, after commit and must be idempotent */ };
const workers = new Map(tenants.map(tenant => [tenant, new DurableOutboxWorker(repositories, tenant, workerId, async message => { await pause('WORKER_PAUSE_BEFORE_HANDLE_MS'); await handle(message); }, verify, maxAttempts, leaseMs)]));
let stopping = false;
const tick = async () => { if (stopping) return; for (const [tenant, worker] of workers) { try { await worker.processOnce(); metrics.set(tenant, await repositories.transaction(tenant, scoped => scoped.getOutboxMetrics(tenant))); } catch (error) { console.error('Outbox worker tick failed', { tenant, error: error instanceof Error ? error.message : 'unknown' }); } } setTimeout(tick, pollMs); };
const reply = (response: ServerResponse, status: number, body: unknown) => { response.statusCode = status; response.setHeader('content-type', 'application/json'); response.end(JSON.stringify(body)); };
const status = async (_request: IncomingMessage, response: ServerResponse) => { const values = await Promise.all(tenants.map(async tenant => [tenant, metrics.get(tenant) ?? await repositories.transaction(tenant, scoped => scoped.getOutboxMetrics(tenant))] as const)); reply(response, 200, { status: 'ready', worker_id: workerId, tenants: Object.fromEntries(values), at_least_once: true }); };
const server = createServer((request, response) => { if (request.method === 'GET' && (request.url === '/healthz' || request.url === '/readyz')) return void status(request, response); reply(response, 404, { error: { code: 'NOT_FOUND' } }); });
server.listen(workerPort, config.host, () => { process.stdout.write(`Transactional outbox worker ${workerId} listening on ${config.host}:${workerPort}\n`); void tick(); });
const shutdown = () => { if (stopping) return; stopping = true; server.close(async () => { await pool.end(); process.exit(0); }); };
process.on('SIGTERM', shutdown); process.on('SIGINT', shutdown);
