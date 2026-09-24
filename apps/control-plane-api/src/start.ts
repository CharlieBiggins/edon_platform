import { createControlPlaneServer } from './server.js';
import { requireRuntimeEnvironment } from './runtime.js';
import { PostgreSQLPlatformRepositories } from '../../../packages/platform-core/src/repositories.js';
import { OidcIdentityVerifier } from '../../../packages/platform-core/src/auth.js';
import { LocalReceiptSigner } from '../../../packages/platform-core/src/receipt-custody.js';

const config = requireRuntimeEnvironment(process.env);
const loadPg = new Function('specifier', 'return import(specifier)') as (specifier: string) => Promise<{ Pool: new (options: { connectionString: string; max?: number }) => { query: (text: string, values?: unknown[]) => Promise<{ rows: unknown[] }>; end: () => Promise<void> } }>;
const pg = await loadPg('pg');
const pool = new pg.Pool({ connectionString: config.databaseUrl, max: 1 });
await pool.query('SELECT 1');
const executor = { query: async <T = unknown>(text: string, values?: unknown[]) => { const tenant = values?.[0]; if (typeof tenant === 'string') await pool.query('SELECT set_config($1, $2, false)', ['app.tenant_id', tenant]); return await pool.query(text, values) as { rows: T[] }; } };
const server = createControlPlaneServer({ profile: config.profile, repositories: new PostgreSQLPlatformRepositories(executor), identityVerifier: new OidcIdentityVerifier(config.oidcIssuer, config.oidcAudience, config.jwksUrl), receiptSigner: new LocalReceiptSigner(config.signingKey), signingKeyMode: 'KMS', tenantIsolation: true, auditLogging: true, corsOrigin: config.corsOrigin });
server.listen(config.port, config.host, () => process.stdout.write(`Control Plane API listening on ${config.host}:${config.port}\n`));
const shutdown = () => server.close(async () => { await pool.end(); process.exit(0); });
process.on('SIGTERM', shutdown); process.on('SIGINT', shutdown);


