import { createControlPlaneServer } from './server.js';
import { requireRuntimeEnvironment } from './runtime.js';
import { PostgreSQLPlatformRepositories } from '../../../packages/platform-core/src/repositories.js';
import { OidcIdentityVerifier } from '../../../packages/platform-core/src/auth.js';
import { AwsKmsProvider, DeterministicKmsProvider, KmsReceiptCustody } from '../../../packages/platform-core/src/receipt-custody.js';

const config = requireRuntimeEnvironment(process.env);
type PgClient = { query: <T = unknown>(text: string, values?: unknown[]) => Promise<{ rows: T[] }>; release: () => void };
type PgPool = { query: <T = unknown>(text: string, values?: unknown[]) => Promise<{ rows: T[] }>; connect: () => Promise<PgClient>; end: () => Promise<void> };
const loadPg = new Function('specifier', 'return import(specifier)') as (specifier: string) => Promise<{ Pool: new (options: { connectionString: string; max?: number }) => PgPool }>;
const pg = await loadPg('pg');
const pool = new pg.Pool({ connectionString: config.databaseUrl, max: 10 });
await pool.query('SELECT 1');
const executor = {
  query: <T = unknown>(text: string, values?: unknown[]) => pool.query<T>(text, values),
  transaction: async <T>(tenantId: string, work: (db: { query: <R = unknown>(text: string, values?: unknown[]) => Promise<{ rows: R[] }> }) => Promise<T>) => {
    const maxAttempts = 3;
    for (let attempt = 1; attempt <= maxAttempts; attempt += 1) {
      const client = await pool.connect();
      try {
        await client.query('BEGIN');
        await client.query('SELECT set_config($1, $2, true)', ['app.tenant_id', tenantId]);
        const result = await work(client);
        await client.query('COMMIT');
        return result;
      } catch (error) {
        try { await client.query('ROLLBACK'); } catch (rollbackError) { console.error('Control Plane rollback failed', rollbackError); }
        const code = typeof error === 'object' && error !== null && 'code' in error ? String((error as { code?: unknown }).code) : '';
        const retryable = code === '40001' || code === '40P01';
        if (!retryable || attempt === maxAttempts) throw error;
        await new Promise(resolve => setTimeout(resolve, 25 * attempt));
      } finally {
        client.release();
      }
    }
    throw new Error('Transaction retry loop exited unexpectedly');
  },
};
const receiptSigner = new KmsReceiptCustody(config.profile === 'STAGING_TEST' ? new DeterministicKmsProvider() : new AwsKmsProvider(), config.profile === 'STAGING_TEST' ? 'kms-test-key' : (config.kmsKeyId ?? ''));
const server = createControlPlaneServer({ profile: config.profile, repositories: new PostgreSQLPlatformRepositories(executor), identityVerifier: new OidcIdentityVerifier(config.oidcIssuer, config.oidcAudience, config.jwksUrl), receiptSigner, signingKeyMode: 'KMS', tenantIsolation: true, auditLogging: true, corsOrigin: config.corsOrigin });
server.listen(config.port, config.host, () => process.stdout.write(`Control Plane API listening on ${config.host}:${config.port}\n`));
const shutdown = () => server.close(async () => { await pool.end(); process.exit(0); });
process.on('SIGTERM', shutdown); process.on('SIGINT', shutdown);


