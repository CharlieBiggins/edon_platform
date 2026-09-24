import { createControlPlaneServer } from './server';
import { requireRuntimeEnvironment } from './runtime';
import { InMemoryPlatformRepositories } from '../../../packages/platform-core/src/repositories';
import { SimulatedIdentityVerifier } from '../../../packages/platform-core/src/auth';
import { LocalReceiptSigner } from '../../../packages/platform-core/src/receipt-custody';

const config = requireRuntimeEnvironment(process.env);
const server = createControlPlaneServer({ profile: config.profile, repositories: new InMemoryPlatformRepositories(), identityVerifier: new SimulatedIdentityVerifier({ tenant_id: 'meridian-demo', actor_id: 'operator-01', actor_type: 'HUMAN', roles: ['operator'], expires_at: '2099-01-01T00:00:00Z' }), receiptSigner: new LocalReceiptSigner(config.signingKey), signingKeyMode: 'KMS', tenantIsolation: true, auditLogging: true });
server.listen(config.port, config.host, () => process.stdout.write(`Control Plane API listening on ${config.host}:${config.port}\n`));
const shutdown = () => server.close(() => process.exit(0));
process.on('SIGTERM', shutdown); process.on('SIGINT', shutdown);
