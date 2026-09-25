import type { EvidenceAdmission } from './contracts.js';
import type { EvidenceRecord } from '../../contracts/src/index.js';
export class DeterministicEvidenceAdmission implements EvidenceAdmission {
  admit(input: unknown): EvidenceRecord[] {
    if (!input || typeof input !== 'object') return [];
    const candidate = input as { evidence_id?: string; status?: EvidenceRecord['status']; source?: string; version?: string; citation_text?: string; trusted_source?: boolean; capacity_units?: unknown };
    if (candidate.trusted_source === false || typeof candidate.capacity_units !== 'number' || candidate.capacity_units < 0 || candidate.capacity_units > 10000) return [];
    return [{ evidence_id: candidate.evidence_id ?? `evidence-${Date.now()}`, status: candidate.status ?? 'observed', source: candidate.source ?? 'observation-gateway', version: candidate.version ?? 'unversioned', citation_text: candidate.citation_text ?? 'Admitted observation payload.' }];
  }
}


