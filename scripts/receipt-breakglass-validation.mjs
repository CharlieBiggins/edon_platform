import { canonicalize, DeterministicKmsProvider, KmsReceiptCustody } from '../apps/control-plane-api/dist/packages/platform-core/src/receipt-custody.js';
import { InMemoryPlatformRepositories } from '../apps/control-plane-api/dist/packages/platform-core/src/repositories.js';
import { mkdir, writeFile } from 'node:fs/promises';

const checks = [];
const check = (name, passed, detail) => { checks.push({ name, passed, detail }); if (!passed) throw new Error(`${name}: ${detail}`); };
const provider = new DeterministicKmsProvider(new Map([['kms-test-key', 'v1'], ['kms-rotated-key', 'v2']]));
const custody = new KmsReceiptCustody(provider, 'kms-test-key');
const payload = canonicalize({ tenant: 'meridian-demo', incident: 'INC-1042', state_version: 142, evidence_versions: { 'EV-2082': 'v8' } });
const signed = await custody.sign(payload);
check('KMS signature verifies', await custody.verify(payload, signed.signature, signed.key_id, signed.key_version), 'valid signature accepted');
check('tampered receipt rejected', !(await custody.verify(`${payload}x`, signed.signature, signed.key_id, signed.key_version)), 'modified canonical payload rejected');
const repos = new InMemoryPlatformRepositories();
await repos.putBreakGlass({ grant_id: 'bg-test', tenant_id: 'meridian-demo', incident_id: 'INC-1042', requested_by: 'operator-01', capabilities: ['evidence:restricted:read'], resources: ['memphis-fulfillment'], justification: 'Investigate carrier evidence gap', duration_seconds: 60, status: 'REQUESTED', requested_at: new Date(0).toISOString() });
const grant = await repos.getBreakGlass('meridian-demo', 'bg-test');
check('break-glass grant is tenant scoped', grant?.tenant_id === 'meridian-demo', 'grant loaded for matching tenant');
check('cross-tenant grant is hidden', (await repos.getBreakGlass('other-tenant', 'bg-test')) === null, 'other tenant cannot read grant');
await mkdir(process.env.ARTIFACT_DIR ?? 'artifacts', { recursive: true });
await writeFile(`${process.env.ARTIFACT_DIR ?? 'artifacts'}/receipt-breakglass-validation.json`, JSON.stringify({ checks, status: 'passed' }, null, 2));
