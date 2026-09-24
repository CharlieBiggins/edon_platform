import { InMemoryPlatformRepositories, type PlatformRepositories } from '../../../packages/platform-core/src/repositories';
import { SimulatedIdentityVerifier, type IdentityVerifier } from '../../../packages/platform-core/src/auth';
import { KmsReceiptCustody, type ReceiptSigner } from '../../../packages/platform-core/src/receipt-custody';

export type RuntimeProfile = 'LOCAL' | 'STAGING_TEST' | 'STAGING' | 'PRODUCTION';
export type RuntimeDependencies = { repositories: PlatformRepositories; identityVerifier: IdentityVerifier; receiptSigner: ReceiptSigner; tenantIsolation: boolean; auditLogging: boolean; signingKeyMode: 'KMS' | 'DEVELOPMENT' };

export function assertRuntimeProfile(profile: RuntimeProfile, dependencies: RuntimeDependencies) {
  if (profile === 'LOCAL') return;
  if (dependencies.repositories instanceof InMemoryPlatformRepositories) throw new Error(`${profile} requires PostgreSQL repositories`);
  if (dependencies.identityVerifier instanceof SimulatedIdentityVerifier) throw new Error(`${profile} requires OIDC identity verification`);
  if (dependencies.receiptSigner instanceof KmsReceiptCustody || dependencies.signingKeyMode !== 'KMS') throw new Error(`${profile} requires KMS receipt custody`);
  if (!dependencies.tenantIsolation) throw new Error(`${profile} requires tenant isolation`);
  if (!dependencies.auditLogging) throw new Error(`${profile} requires audit logging`);
}
