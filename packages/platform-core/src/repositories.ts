import type { DecisionReceipt, EventEnvelope, EvidenceRecord, OutcomeRecord, ActionProposal, KernelDecision } from '../../contracts/src/index.js';

export type StoredIncident = { incident_id: string; tenant_id: string; scope_id: string; state_version: number; status: string; values?: Record<string, unknown> };
export type StoredReview = { review_id: string; proposal_id: string; actor_id: string; approved: boolean; recorded_at: string };
export type StoredShadow = { proposal_id: string; recorded_at: string; executed: false; credentials: 'NONE' };
export type StoredKernelDecision = KernelDecision & { tenant_id: string; recorded_at?: string };

export interface PlatformRepositories {
  transaction<T>(tenantId: string, work: (repositories: PlatformRepositories) => Promise<T>): Promise<T>;
  appendEvent(event: EventEnvelope): Promise<boolean>;
  getEvents(tenantId: string, incidentId?: string): Promise<EventEnvelope[]>;
  putEvidence(record: EvidenceRecord & { tenant_id: string }): Promise<void>;
  getState(tenantId: string, scopeId: string): Promise<{ version: number; values: Record<string, unknown> } | null>;
  putState(incident: StoredIncident, expectedVersion: number): Promise<boolean>;
  putIncident(incident: StoredIncident): Promise<void>;
  putProposal(proposal: ActionProposal & { tenant_id: string }): Promise<void>;
  getProposal(tenantId: string, proposalId: string): Promise<(ActionProposal & { tenant_id: string }) | null>;
  putReview(review: StoredReview & { tenant_id: string }): Promise<void>;
  putKernelDecision(decision: StoredKernelDecision): Promise<void>;
  getKernelDecision(tenantId: string, proposalId: string): Promise<StoredKernelDecision | null>;
  putMandate(mandate: Record<string, unknown> & { tenant_id: string }): Promise<void>;
  putShadow(shadow: StoredShadow & { tenant_id: string }): Promise<void>;
  putOutcome(outcome: OutcomeRecord & { tenant_id: string }): Promise<void>;
  getOutcome(tenantId: string, outcomeId: string): Promise<(OutcomeRecord & { tenant_id: string }) | null>;
  putReceipt(receipt: DecisionReceipt & { tenant_id: string }): Promise<void>;
  getReceipt(tenantId: string, receiptId: string): Promise<(DecisionReceipt & { tenant_id: string }) | null>;
  getIdempotency(tenantId: string, key: string): Promise<unknown | undefined>;
  claimIdempotency(tenantId: string, key: string, response: unknown): Promise<{ claimed: boolean; response: unknown }>;
}

export class InMemoryPlatformRepositories implements PlatformRepositories {
  private events: EventEnvelope[] = []; private states = new Map<string, { version: number; values: Record<string, unknown> }>(); private receipts = new Map<string, DecisionReceipt & { tenant_id: string }>(); private proposals = new Map<string, ActionProposal & { tenant_id: string }>(); private decisions = new Map<string, StoredKernelDecision>(); private outcomes = new Map<string, OutcomeRecord & { tenant_id: string }>(); private idempotency = new Map<string, unknown>();
  async transaction<T>(_tenantId: string, work: (repositories: PlatformRepositories) => Promise<T>): Promise<T> { return work(this); }
  async appendEvent(event: EventEnvelope) { if (this.events.some(existing => existing.tenant_id === event.tenant_id && existing.event_id === event.event_id)) return false; this.events.push(structuredClone(event)); return true; }
  async getEvents(tenantId: string, incidentId?: string): Promise<EventEnvelope[]> { return this.events.filter(event => event.tenant_id === tenantId && (!incidentId || event.incident_id === incidentId)).map(event => structuredClone(event)); }
  async putEvidence() {}
  async getState(_tenantId: string, _scopeId: string) { return null; }
  async putState(incident: StoredIncident, expectedVersion: number) { if (incident.state_version !== expectedVersion && incident.state_version !== expectedVersion + 1) return false; this.states.set(`${incident.tenant_id}:${incident.scope_id}`, { version: incident.state_version, values: structuredClone(incident.values ?? {}) }); return true; }
  async putIncident() {}
  async putProposal(proposal: ActionProposal & { tenant_id: string }) { this.proposals.set(`${proposal.tenant_id}:${proposal.proposal_id}`, structuredClone(proposal)); }
  async getProposal(tenantId: string, proposalId: string) { return this.proposals.get(`${tenantId}:${proposalId}`) ?? null; }
  async putReview() {}
  async putKernelDecision(decision: StoredKernelDecision) { this.decisions.set(`${decision.tenant_id}:${decision.proposal_id}`, structuredClone(decision)); }
  async getKernelDecision(tenantId: string, proposalId: string) { return this.decisions.get(`${tenantId}:${proposalId}`) ?? null; }
  async putMandate() {}
  async putShadow() {}
  async putOutcome(outcome: OutcomeRecord & { tenant_id: string }) { this.outcomes.set(`${outcome.tenant_id}:${outcome.outcome_id}`, structuredClone(outcome)); }
  async getOutcome(tenantId: string, outcomeId: string) { return this.outcomes.get(`${tenantId}:${outcomeId}`) ?? null; }
  async putReceipt(receipt: DecisionReceipt & { tenant_id: string }) { this.receipts.set(`${receipt.tenant_id}:${receipt.receipt_id}`, structuredClone(receipt)); }
  async getReceipt(tenantId: string, receiptId: string) { return this.receipts.get(`${tenantId}:${receiptId}`) ?? null; }
  async getIdempotency(tenantId: string, key: string) { return this.idempotency.get(`${tenantId}:${key}`); }
  async claimIdempotency(tenantId: string, key: string, response: unknown) { const id = `${tenantId}:${key}`; if (this.idempotency.has(id)) return { claimed: false, response: this.idempotency.get(id) }; this.idempotency.set(id, structuredClone(response)); return { claimed: true, response }; }
}

/** Adapter contract for pg.Pool; production wiring supplies the query/transaction implementation. */
export interface SqlExecutor {
  query<T = unknown>(text: string, values?: unknown[]): Promise<{ rows: T[] }>;
  transaction?<T>(tenantId: string, work: (db: SqlExecutor) => Promise<T>): Promise<T>;
}
export class PostgreSQLPlatformRepositories implements PlatformRepositories {
  constructor(private readonly db: SqlExecutor) {}
  async transaction<T>(tenantId: string, work: (repositories: PlatformRepositories) => Promise<T>): Promise<T> {
    if (!this.db.transaction) return work(this);
    return this.db.transaction(tenantId, async scopedDb => work(new PostgreSQLPlatformRepositories(scopedDb)));
  }
  async appendEvent(event: EventEnvelope) { const result = await this.db.query('INSERT INTO journal_events (tenant_id,event_id,event_type,payload,recorded_at) VALUES ($1,$2,$3,$4,$5) ON CONFLICT (tenant_id,event_id) DO NOTHING RETURNING event_id', [event.tenant_id, event.event_id, event.event_type, JSON.stringify(event), event.recorded_at]); return result.rows.length === 1; }
  async getEvents(tenantId: string, incidentId?: string) { const result = await this.db.query<EventEnvelope>('SELECT payload FROM journal_events WHERE tenant_id=$1 AND ($2::text IS NULL OR payload->>\'incident_id\'=$2) ORDER BY recorded_at,event_id', [tenantId, incidentId ?? null]); return result.rows.map(row => (row as unknown as { payload: EventEnvelope }).payload); }
  async putEvidence(record: EvidenceRecord & { tenant_id: string }) { await this.db.query('INSERT INTO evidence_records (tenant_id,evidence_id,payload) VALUES ($1,$2,$3) ON CONFLICT (tenant_id,evidence_id) DO NOTHING', [record.tenant_id, record.evidence_id, JSON.stringify(record)]); }
  async getState(tenantId: string, scopeId: string) { const result = await this.db.query<{ version: number; values: Record<string, unknown> }>('SELECT version,values FROM state_snapshots WHERE tenant_id=$1 AND scope_id=$2', [tenantId, scopeId]); return result.rows[0] ?? null; }
  async putState(incident: StoredIncident, expectedVersion: number) { const result = await this.db.query('INSERT INTO state_snapshots (tenant_id,scope_id,version,values) VALUES ($1,$2,$3,$5) ON CONFLICT (tenant_id,scope_id) DO UPDATE SET version=EXCLUDED.version, values=EXCLUDED.values WHERE state_snapshots.version=$4 RETURNING scope_id', [incident.tenant_id, incident.scope_id, incident.state_version, expectedVersion, JSON.stringify(incident.values ?? {})]); return result.rows.length === 1; }
  async putIncident(incident: StoredIncident) { await this.db.query('INSERT INTO incidents (tenant_id,incident_id,scope_id,state_version,status) VALUES ($1,$2,$3,$4,$5) ON CONFLICT (tenant_id,incident_id) DO UPDATE SET state_version=EXCLUDED.state_version,status=EXCLUDED.status', [incident.tenant_id, incident.incident_id, incident.scope_id, incident.state_version, incident.status]); }
  async putProposal(proposal: ActionProposal & { tenant_id: string }) { await this.db.query('INSERT INTO proposals (tenant_id,proposal_id,payload) VALUES ($1,$2,$3) ON CONFLICT (tenant_id,proposal_id) DO NOTHING', [proposal.tenant_id, proposal.proposal_id, JSON.stringify(proposal)]); }
  async getProposal(tenantId: string, proposalId: string) { const result = await this.db.query<{ payload: ActionProposal & { tenant_id: string } }>('SELECT payload FROM proposals WHERE tenant_id=$1 AND proposal_id=$2', [tenantId, proposalId]); return result.rows[0]?.payload ?? null; }
  async putReview(review: StoredReview & { tenant_id: string }) { await this.db.query('INSERT INTO human_reviews (tenant_id,review_id,payload) VALUES ($1,$2,$3)', [review.tenant_id, review.review_id, JSON.stringify(review)]); }
  async putKernelDecision(decision: StoredKernelDecision) { await this.db.query('INSERT INTO kernel_decisions (tenant_id,decision_id,proposal_id,payload,recorded_at) VALUES ($1,$2,$3,$4,$5) ON CONFLICT (tenant_id,decision_id) DO NOTHING', [decision.tenant_id, decision.decision_id, decision.proposal_id, JSON.stringify(decision), decision.recorded_at ?? decision.evaluated_at]); }
  async getKernelDecision(tenantId: string, proposalId: string) { const result = await this.db.query<{ payload: StoredKernelDecision }>('SELECT payload FROM kernel_decisions WHERE tenant_id=$1 AND proposal_id=$2 ORDER BY recorded_at DESC LIMIT 1', [tenantId, proposalId]); return result.rows[0]?.payload ?? null; }
  async putMandate(mandate: Record<string, unknown> & { tenant_id: string }) { await this.db.query('INSERT INTO mandates (tenant_id,mandate_id,payload) VALUES ($1,$2,$3)', [mandate.tenant_id, String(mandate.mandate_id), JSON.stringify(mandate)]); }
  async putShadow(shadow: StoredShadow & { tenant_id: string }) { await this.db.query('INSERT INTO shadow_evaluations (tenant_id,proposal_id,payload) VALUES ($1,$2,$3)', [shadow.tenant_id, shadow.proposal_id, JSON.stringify(shadow)]); }
  async putOutcome(outcome: OutcomeRecord & { tenant_id: string }) { await this.db.query('INSERT INTO outcomes (tenant_id,outcome_id,payload) VALUES ($1,$2,$3) ON CONFLICT (tenant_id,outcome_id) DO NOTHING', [outcome.tenant_id, outcome.outcome_id, JSON.stringify(outcome)]); }
  async getOutcome(tenantId: string, outcomeId: string) { const result = await this.db.query<{ payload: OutcomeRecord & { tenant_id: string } }>('SELECT payload FROM outcomes WHERE tenant_id=$1 AND outcome_id=$2', [tenantId, outcomeId]); return result.rows[0]?.payload ?? null; }
  async putReceipt(receipt: DecisionReceipt & { tenant_id: string }) { await this.db.query('INSERT INTO receipts (tenant_id,receipt_id,payload) VALUES ($1,$2,$3)', [receipt.tenant_id, receipt.receipt_id, JSON.stringify(receipt)]); }
  async getReceipt(tenantId: string, receiptId: string) { const result = await this.db.query<{ payload: DecisionReceipt & { tenant_id: string } }>('SELECT payload FROM receipts WHERE tenant_id=$1 AND receipt_id=$2', [tenantId, receiptId]); return result.rows[0]?.payload ?? null; }
  async getIdempotency(tenantId: string, key: string) { const result = await this.db.query<{ response: unknown }>('SELECT response FROM idempotency_keys WHERE tenant_id=$1 AND key=$2', [tenantId, key]); return result.rows[0]?.response; }
  async claimIdempotency(tenantId: string, key: string, response: unknown) { const result = await this.db.query<{ response: unknown }>('INSERT INTO idempotency_keys (tenant_id,key,response) VALUES ($1,$2,$3) ON CONFLICT (tenant_id,key) DO NOTHING RETURNING response', [tenantId, key, JSON.stringify(response)]); if (result.rows.length) return { claimed: true, response }; const existing = await this.db.query<{ response: unknown }>('SELECT response FROM idempotency_keys WHERE tenant_id=$1 AND key=$2', [tenantId, key]); return { claimed: false, response: existing.rows[0]?.response }; }
}


