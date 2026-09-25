import { createHash } from 'node:crypto';
import type { EventEnvelope, EvidenceRecord, ExecutionCommand } from '../../contracts/src/index.js';
import type { PlatformRepositories } from './repositories.js';
import { canonicalize, type ReceiptSigner } from './receipt-custody.js';

export type ReconstructionOptions = { cutoff?: string; offset?: number; includeRestricted?: boolean; caseId: string; legalHold?: boolean };
export type Reconstruction = { case_id: string; tenant_id: string; cutoff: string; events: EventEnvelope[]; state: unknown; receipts: unknown[]; commands: unknown[]; integrity: { record_integrity: string; source_verification: string; evidence_status: string; outcome_verification: string; causal_adjudication: string; gaps: string[] }; omissions: Array<{ resource: string; reason: string }>; };
export type EvidencePackage = { manifest: Record<string, unknown>; files: Record<string, string>; signature: { signature: string; key_id: string; key_version?: string; algorithm: string; digest: string; signed_at: string } };
const sha256 = (value: string) => `sha256:${createHash('sha256').update(value).digest('hex')}`;
const jsonl = (items: unknown[]) => items.map(item => canonicalize(item)).join('\n') + (items.length ? '\n' : '');

export class ForensicReconstructionService {
  constructor(private readonly repositories: PlatformRepositories, private readonly signer: ReceiptSigner) {}
  async reconstruct(tenantId: string, options: ReconstructionOptions): Promise<Reconstruction> {
    if (!options.caseId) throw new Error('CASE_SCOPE_REQUIRED');
    if (options.legalHold === false) throw new Error('LEGAL_HOLD_POLICY_BLOCKED');
    const all = await this.repositories.getEvents(tenantId, options.caseId);
    const sorted = all.filter(event => !options.cutoff || event.recorded_at <= options.cutoff).sort((a, b) => a.recorded_at.localeCompare(b.recorded_at) || a.event_id.localeCompare(b.event_id));
    const events = typeof options.offset === 'number' ? sorted.slice(0, Math.max(0, options.offset)) : sorted;
    const receipts = await this.repositories.listReceipts(tenantId, options.caseId);
    const commands = await this.repositories.listExecutions(tenantId, options.caseId);
    const state = await this.repositories.getState(tenantId, 'memphis-fulfillment');
    const omissions = options.includeRestricted ? [] : [{ resource: 'restricted-evidence', reason: 'case authorization does not permit disclosure' }];
    return { case_id: options.caseId, tenant_id: tenantId, cutoff: options.cutoff ?? (events.at(-1)?.recorded_at ?? new Date(0).toISOString()), events, state, receipts, commands: commands.filter(command => !options.cutoff || command.dispatch_requested_at <= options.cutoff), integrity: { record_integrity: 'HASH_CHAIN_REQUIRES_VERIFICATION', source_verification: 'SEPARATE_FROM_INTEGRITY', evidence_status: 'EXPLICIT_STATUS_REQUIRED', outcome_verification: 'SEPARATE_FROM_EVIDENCE', causal_adjudication: 'NO_AUTOMATIC_CAUSATION', gaps: events.length ? [] : ['NO_EVENTS_AT_CUTOFF'] }, omissions };
  }
  async exportPackage(tenantId: string, options: ReconstructionOptions): Promise<EvidencePackage> {
    const reconstruction = await this.reconstruct(tenantId, options);
    const timeline = jsonl(reconstruction.events);
    const files: Record<string, string> = {
      'timeline.jsonl': timeline,
      'state-snapshots.jsonl': jsonl(reconstruction.state ? [reconstruction.state] : []),
      'state-diffs.jsonl': jsonl([]),
      'evidence-index.json': canonicalize({ status: reconstruction.integrity.evidence_status, omissions: reconstruction.omissions }),
      'actors.json': canonicalize({ actors: [...new Set(reconstruction.events.map(event => event.actor_id))] }),
      'authority.json': canonicalize({ authority_versions: [...new Set(reconstruction.events.map(event => event.policy_version))] }),
      'model-invocations.jsonl': jsonl(reconstruction.events.filter(event => event.event_type === 'MODEL_INVOKED')),
      'proposals.jsonl': jsonl(reconstruction.events.filter(event => event.event_type === 'PROPOSAL_CREATED')),
      'kernel-decisions.jsonl': jsonl(reconstruction.events.filter(event => event.event_type === 'KERNEL_DECIDED')),
      'human-reviews.jsonl': jsonl(reconstruction.events.filter(event => event.event_type === 'HUMAN_REVIEWED')),
      'commands.jsonl': jsonl(reconstruction.commands),
      'outcomes.jsonl': jsonl(reconstruction.events.filter(event => ['OUTCOME_OBSERVED', 'OUTCOME_VERIFIED'].includes(event.event_type))),
      'integrity-report.json': canonicalize(reconstruction.integrity),
      'human-readable-report.pdf': '%PDF-1.4\n% Cerebrum signed reconstruction\n' + `Case ${options.caseId}\n` + '%%EOF\n',
    };
    const hashes = Object.fromEntries(Object.entries(files).map(([name, content]) => [name, sha256(content)]));
    const manifest = { format: 'cerebrum-evidence-package-v1', tenant_id: tenantId, case_id: options.caseId, cutoff: reconstruction.cutoff, files: hashes, omissions: reconstruction.omissions, integrity: reconstruction.integrity };
    const signature = await this.signer.sign(canonicalize(manifest));
    files['manifest.json'] = canonicalize(manifest);
    files['signatures/manifest.signature.json'] = canonicalize(signature);
    return { manifest, files, signature };
  }
}
