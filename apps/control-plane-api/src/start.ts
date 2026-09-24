import { createControlPlaneServer } from './server.js';
import { requireRuntimeEnvironment } from './runtime.js';
import { PostgreSQLPlatformRepositories } from '../../../packages/platform-core/src/repositories.js';
import { SimulatedIdentityVerifier } from '../../../packages/platform-core/src/auth.js';
import { LocalReceiptSigner } from '../../../packages/platform-core/src/receipt-custody.js';

const config = requireRuntimeEnvironment(process.env);
const loadPg = new Function('specifier', 'return import(specifier)') as (specifier: string) => Promise<{ Pool: new (options: { connectionString: string }) => { query: (text: string, values?: unknown[]) => Promise<{ rows: unknown[] }>; end: () => Promise<void> } }>;
const pg = await loadPg('pg');
const pool = new pg.Pool({ connectionString: config.databaseUrl });
await pool.query('SELECT 1');
const executor = { query: async <T = unknown>(text: string, values?: unknown[]) => await pool.query(text, values) as { rows: T[] } };
const server = createControlPlaneServer({ profile: config.profile, repositories: new PostgreSQLPlatformRepositories(executor), identityVerifier: new SimulatedIdentityVerifier({ tenant_id: 'meridian-demo', actor_id: 'operator-01', actor_type: 'HUMAN', roles: ['operator'], expires_at: '2099-01-01T00:00:00Z' }), receiptSigner: new LocalReceiptSigner(config.signingKey), signingKeyMode: 'KMS', tenantIsolation: true, auditLogging: true });
server.listen(config.port, config.host, () => process.stdout.write(`Control Plane API listening on ${config.host}:${config.port}\n`));
const shutdown = () => server.close(async () => { await pool.end(); process.exit(0); });
process.on('SIGTERM', shutdown); process.on('SIGINT', shutdown);


