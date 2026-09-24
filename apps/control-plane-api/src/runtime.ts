import { InMemoryPlatformRepositories, type PlatformRepositories } from '../../../packages/platform-core/src/repositories';
import { SimulatedIdentityVerifier, type IdentityVerifier } from '../../../packages/platform-core/src/auth';
import { KmsReceiptCustody, type ReceiptSigner } from '../../../packages/platform-core/src/receipt-custody';

export type RuntimeProfile = 'LOCAL' | 'STAGING_TEST' | 'STAGING' | 'PRODUCTION';
export type RuntimeDependencies = { repositories: PlatformRepositories; identityVerifier: IdentityVerifier; receiptSigner: ReceiptSigner; tenantIsolation: boolean; auditLogging: boolean; signingKeyMode: 'KMS' | 'DEVELOPMENT' };

export function assertRuntimeProfile(profile: RuntimeProfile, dependencies: RuntimeDependencies) {
  if (profile === 'LOCAL') return;
  if (profile !== 'STAGING_TEST' && dependencies.repositories instanceof InMemoryPlatformRepositories) throw new Error(`${profile} requires PostgreSQL repositories`);
  if (profile !== 'STAGING_TEST' && dependencies.identityVerifier instanceof SimulatedIdentityVerifier) throw new Error(`${profile} requires OIDC identity verification`);
  if (dependencies.receiptSigner instanceof KmsReceiptCustody || dependencies.signingKeyMode !== 'KMS') throw new Error(`${profile} requires KMS receipt custody`);
  if (!dependencies.tenantIsolation) throw new Error(`${profile} requires tenant isolation`);
  if (!dependencies.auditLogging) throw new Error(`${profile} requires audit logging`);
}

export function requireRuntimeEnvironment(env: Record<string, string | undefined>) {
  const required = ['RUNTIME_PROFILE', 'DATABASE_URL', 'MIGRATOR_ROLE', 'APPLICATION_ROLE', 'OIDC_ISSUER', 'OIDC_AUDIENCE', 'OIDC_JWKS_URL', 'RECEIPT_SIGNING_TEST_KEY', 'AUDIT_LOGGING', 'TENANT_ISOLATION_ENFORCEMENT', 'API_HOST', 'API_PORT'];
  const missing = required.filter(name => !env[name]);
  if (missing.length) throw new Error(`Missing mandatory runtime configuration: ${missing.join(', ')}`);
  if (env.RUNTIME_PROFILE !== 'STAGING_TEST') throw new Error('The CI server entrypoint only accepts RUNTIME_PROFILE=STAGING_TEST');
  if (env.AUDIT_LOGGING !== 'true' || env.TENANT_ISOLATION_ENFORCEMENT !== 'true') throw new Error('Audit logging and tenant isolation must be enabled');
  return { profile: 'STAGING_TEST' as const, host: env.API_HOST!, port: Number(env.API_PORT), databaseUrl: env.DATABASE_URL!, oidcIssuer: env.OIDC_ISSUER!, oidcAudience: env.OIDC_AUDIENCE!, jwksUrl: env.OIDC_JWKS_URL!, signingKey: env.RECEIPT_SIGNING_TEST_KEY! };
}
