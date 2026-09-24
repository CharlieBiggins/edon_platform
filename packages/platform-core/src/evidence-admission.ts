import type { EvidenceAdmission } from './contracts.js';
import type { EvidenceRecord } from '../../contracts/src/index.js';
export class DeterministicEvidenceAdmission implements EvidenceAdmission {
  admit(input: unknown): EvidenceRecord[] {
    if (!input || typeof input !== 'object') return [];
    const candidate = input as { event?: string; trusted_source?: boolean };
    if (candidate.event !== 'capacity_disruption' || candidate.trusted_source === false) return [];
    return [
      { evidence_id: 'EV-2081', status: 'observed', source: 'WMS event feed', version: 'v3', citation_text: 'Memphis outbound capacity observed at 260 units.' },
      { evidence_id: 'EV-2082', status: 'verified', source: 'Commitment ledger', version: 'v8', citation_text: 'Four commitments are at risk.' },
      { evidence_id: 'EV-2085', status: 'missing', source: 'Carrier liaison', version: 'pending', citation_text: 'Carrier capacity confirmation is missing.' },
    ];
  }
}


