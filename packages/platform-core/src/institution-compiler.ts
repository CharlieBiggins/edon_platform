import { createHash } from 'node:crypto';

export const INSTITUTION_BUILDER_STAGES = [
  'Sources', 'Classification', 'Extraction', 'IR Mapping', 'Validation',
  'Authority & Policy', 'Control Graph', 'Simulation', 'Review & Sign', 'Deployment',
] as const;
export type InstitutionBuilderStage = typeof INSTITUTION_BUILDER_STAGES[number];
export type CompilerStatus = 'DRAFT' | 'CANDIDATE' | 'VALIDATED' | 'SIGNED' | 'SHADOW_DEPLOYED' | 'PROMOTED' | 'ROLLED_BACK';
export type SourceSensitivity = 'PUBLIC' | 'INTERNAL' | 'RESTRICTED' | 'HIGHLY_RESTRICTED';

export interface InstitutionSource { source_id: string; tenant_id: string; kind: string; version: string; owner: string; sensitivity: SourceSensitivity; effective_at: string; content_hash: string; provenance: string; }
export interface InstitutionObject { object_id: string; type: string; canonical_name: string; source_ids: string[]; attributes: Record<string, unknown>; }
export interface ValidationIssue { issue_id: string; severity: 'ERROR' | 'WARNING'; code: string; message: string; source_ids: string[]; resolved: boolean; }
export interface InstitutionCandidate { candidate_id: string; tenant_id: string; institution_id: string; version: string; compiler_version: string; source_ids: string[]; input_source_hashes: string[]; objects: InstitutionObject[]; issues: ValidationIssue[]; graph_hash: string; control_graph_diff: Record<string, unknown>; previous_candidate_id?: string; status: CompilerStatus; created_at: string; }
export interface InstitutionRelease { release_id: string; tenant_id: string; institution_id: string; candidate_id: string; version: string; manifest_hash: string; signature_status: 'SIGNATURE_PENDING' | 'SIGNED'; status: CompilerStatus; signed_by?: string; signed_at?: string; shadow_deployed_at?: string; previous_release_id?: string; rollback_target?: string; }

export interface InstitutionCompilerStore {
  putCandidate(candidate: InstitutionCandidate): Promise<void>;
  getCandidate(tenantId: string, candidateId: string): Promise<InstitutionCandidate | null>;
  putRelease(release: InstitutionRelease): Promise<void>;
  getRelease(tenantId: string, releaseId: string): Promise<InstitutionRelease | null>;
}

const hash = (value: unknown) => `sha256:${createHash('sha256').update(JSON.stringify(value)).digest('hex')}`;

/** Deterministic compiler boundary. It proposes institutional objects; it never activates authority. */
export class DeterministicInstitutionCompiler {
  constructor(private readonly store: InstitutionCompilerStore) {}

  async compileCandidate(tenantId: string, sources: InstitutionSource[], now: string, candidateId = `candidate-${hash(sources).slice(-12)}`): Promise<InstitutionCandidate> {
    if (!tenantId || sources.length === 0) throw new Error('At least one tenant-scoped source is required');
    if (sources.some(source => source.tenant_id !== tenantId)) throw new Error('Source tenant mismatch');
    const objects = sources.map((source, index) => ({ object_id: `${candidateId}:object:${index + 1}`, type: source.kind, canonical_name: source.kind.replaceAll('_', ' '), source_ids: [source.source_id], attributes: { source_version: source.version, sensitivity: source.sensitivity, provenance: source.provenance } }));
    const issues: ValidationIssue[] = sources.map(source => ({ issue_id: `${candidateId}:issue:${source.source_id}`, severity: source.owner && source.effective_at ? 'WARNING' : 'ERROR', code: source.owner && source.effective_at ? 'SOURCE_METADATA_RECORDED' : 'SOURCE_METADATA_MISSING', message: source.owner && source.effective_at ? 'Source metadata is recorded.' : 'Source owner and effective date are required.', source_ids: [source.source_id], resolved: Boolean(source.owner && source.effective_at) }));
    const graphHash = hash({ tenantId, sources: sources.map(source => ({ id: source.source_id, version: source.version, content_hash: source.content_hash })), objects });
    const candidate: InstitutionCandidate = { candidate_id: candidateId, tenant_id: tenantId, institution_id: 'default', version: '1.0.0', compiler_version: 'compiler-reference-0.1.0', source_ids: sources.map(source => source.source_id), input_source_hashes: sources.map(source => source.content_hash), objects, issues, graph_hash: graphHash, control_graph_diff: {}, status: 'CANDIDATE', created_at: now };
    await this.store.putCandidate(candidate);
    return candidate;
  }

  async validate(tenantId: string, candidateId: string): Promise<InstitutionCandidate> {
    const candidate = await this.store.getCandidate(tenantId, candidateId);
    if (!candidate) throw new Error('Candidate not found');
    if (candidate.tenant_id !== tenantId) throw new Error('Candidate tenant mismatch');
    const errors = candidate.issues.filter(issue => issue.severity === 'ERROR' && !issue.resolved);
    if (errors.length) return { ...candidate, status: 'CANDIDATE' };
    const validated = { ...candidate, status: 'VALIDATED' as const };
    await this.store.putCandidate(validated);
    return validated;
  }

  async sign(tenantId: string, candidateId: string, reviewerId: string, now: string): Promise<InstitutionRelease> {
    if (!reviewerId) throw new Error('Authorized reviewer is required');
    const candidate = await this.validate(tenantId, candidateId);
    if (candidate.status !== 'VALIDATED') throw new Error('Validation gate has not passed');
    const release: InstitutionRelease = { release_id: `release-${candidate.candidate_id}`, tenant_id: tenantId, institution_id: candidate.institution_id, candidate_id: candidate.candidate_id, version: candidate.version, manifest_hash: candidate.graph_hash, signature_status: 'SIGNATURE_PENDING', status: 'SIGNED', signed_by: reviewerId, signed_at: now, rollback_target: undefined };
    await this.store.putRelease(release);
    return release;
  }

  async deployShadow(tenantId: string, releaseId: string, now: string): Promise<InstitutionRelease> {
    const release = await this.store.getRelease(tenantId, releaseId);
    if (!release || release.tenant_id !== tenantId) throw new Error('Release not found');
    if (release.status !== 'SIGNED') throw new Error('Only signed releases may enter shadow mode');
    const deployed = { ...release, status: 'SHADOW_DEPLOYED' as const, shadow_deployed_at: now };
    await this.store.putRelease(deployed);
    return deployed;
  }
}
