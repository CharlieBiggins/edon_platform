import { mkdir, writeFile } from 'node:fs/promises';
import { DeterministicKernel } from '../apps/control-plane-api/dist/packages/platform-core/src/kernel.js';
import { HumanReviewGate } from '../apps/control-plane-api/dist/packages/platform-core/src/human-review.js';
import { InMemoryPlatformRepositories } from '../apps/control-plane-api/dist/packages/platform-core/src/repositories.js';

const checks = [];
const check = (name, passed, detail) => { checks.push({ name, passed, detail }); if (!passed) throw new Error(`${name}: ${detail}`); };
const base = { proposal_id: 'PROP-VALIDATION', incident_id: 'INC-1042', objective: 'Protect commitments', actions: ['reserve capacity'], modeled_cost: 24600, commitments_protected: 4, assumptions: [], citations: ['EV-1'], state_version: 142, policy_version: 'POL-LOG-07 v18', status: 'PENDING_KERNEL', proposal_hash: 'sha256:proposal', context: { tenant_id: 'meridian-demo', incident_id: 'INC-1042', state_version: 142, state_hash: 'state-hash', evidence_versions: { 'EV-1': 'v1' }, policy_version: 'POL-LOG-07 v18', authority_version: 'AUTH-v1', mandate_version: 'MND-v1', commitment_version: 'CMT-v1', c1_release: 'c1-shadow-0.9.1', adapter_version: 'adapter-v1', actionnet_version: 'actionnet-v0.4', domain_pack_version: 'logistics-v1', capability_id: 'c1.institutional-assessment', operating_mode: 'SHADOW' } };
const kernel = new DeterministicKernel();
check('stale proposal abstains', kernel.evaluateAt(base, 143, 30000).disposition === 'ABSTAIN', 'state version mismatch cannot allow');
check('model timeout abstains', kernel.evaluateAt({ ...base, assumptions: ['MODEL_TIMEOUT'] }, 142, 30000).disposition === 'ABSTAIN', 'invalid model output cannot allow');
check('approval limit denies', new HumanReviewGate().reevaluate(base, true, 142, 10000).disposition === 'DENY', 'mandate limit is enforced by Kernel');
check('human rejection requests revision', new HumanReviewGate().reevaluate(base, false, 142, 30000).disposition === 'REVISE', 'human rejection cannot become authorization');
const repos = new InMemoryPlatformRepositories();
await repos.putProposal({ ...base, tenant_id: 'meridian-demo' });
await repos.putProposal({ ...base, objective: 'altered', tenant_id: 'meridian-demo' });
check('proposal is immutable', (await repos.getProposal('meridian-demo', base.proposal_id))?.objective === 'Protect commitments', 'duplicate proposal cannot overwrite binding');
await mkdir(process.env.ARTIFACT_DIR ?? 'artifacts', { recursive: true });
await writeFile(`${process.env.ARTIFACT_DIR ?? 'artifacts'}/proposal-kernel-review-validation.json`, JSON.stringify({ checks, status: 'passed' }, null, 2));
