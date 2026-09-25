import type { DecisionReceipt, EventEnvelope, EvidenceRecord, OutcomeRecord, ActionProposal, KernelDecision } from '../../contracts/src/index.js';

export type StoredIncident = { incident_id: string; tenant_id: string; scope_id: string; state_version: number; status: string; values?: Record<string, unknown>; state_hash?: string };
export type StateDiff = { tenant_id: string; scope_id: string; version: number; diff: Record<string, unknown>; state_hash: string };
export type EvidenceRelationship = { tenant_id: string; relationship_id: string; event_id: string; evidence_id: string; relationship_type: 'ADMITTED_FOR' | 'RESTRICTED_FROM' | 'DISPUTED_BY' | 'REJECTED_FOR' };
export type StoredReview = { review_id: string; proposal_id: string; actor_id: string; approved: boolean; recorded_at: string };
export type StoredShadow = { proposal_id: string; recorded_at: string; executed: false; credentials: 'NONE' };
export type StoredKernelDecision = KernelDecision & { tenant_id: string; recorded_at?: string };
export type OutboxMessage = { outbox_id: string; tenant_id: string; dedupe_key: string; topic: string; aggregate_id: string; payload: Record<string, unknown>; correlation_id: string; trace_id: string; state_version?: number; status?: 'PENDING' | 'PROCESSING' | 'COMPLETED' | 'DEAD_LETTER'; attempts?: number; available_at?: string; lease_expires_at?: string; worker_id?: string; last_error?: string; last_error_code?: string; last_error_metadata?: Record<string, unknown> };

export interface PlatformRepositories {
  transaction<T>(tenantId: string, work: (repositories: PlatformRepositories) => Promise<T>): Promise<T>;
  lockScope(scopeId: string): Promise<void>;
  appendEvent(event: EventEnvelope): Promise<boolean>;
  getEvents(tenantId: string, incidentId?: string): Promise<EventEnvelope[]>;
  putEvidence(record: EvidenceRecord & { tenant_id: string }): Promise<void>;
  getState(tenantId: string, scopeId: string): Promise<{ version: number; values: Record<string, unknown> } | null>;
  putState(incident: StoredIncident, expectedVersion: number): Promise<boolean>;
  putStateDiff(diff: StateDiff): Promise<void>;
  linkEvidence(relationship: EvidenceRelationship): Promise<void>;
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
  enqueueOutbox(message: OutboxMessage): Promise<boolean>;
  claimOutbox(tenantId: string, workerId: string, leaseMs?: number): Promise<OutboxMessage | null>;
  completeOutbox(tenantId: string, outboxId: string): Promise<void>;
  retryOutbox(tenantId: string, outboxId: string, error: string, maxAttempts?: number, delayMs?: number): Promise<'RETRYING' | 'DEAD_LETTER'>;
  getOutboxMetrics(tenantId: string): Promise<{ pending: number; processing: number; completed: number; dead_letter: number; oldest_age_ms: number | null; retries: number }>;
  requeueOutbox(tenantId: string, outboxId: string): Promise<boolean>;
  getActorMembership(tenantId: string, actorId: string, role: string): Promise<{ active: boolean; facility_scope: string | null; mandate_expires_at: string | null; financial_limit: number | null } | null>;
}

export class InMemoryPlatformRepositories implements PlatformRepositories {
  private events: EventEnvelope[] = []; private states = new Map<string, { version: number; values: Record<string, unknown> }>(); private receipts = new Map<string, DecisionReceipt & { tenant_id: string }>(); private proposals = new Map<string, ActionProposal & { tenant_id: string }>(); private decisions = new Map<string, StoredKernelDecision>(); private outcomes = new Map<string, OutcomeRecord & { tenant_id: string }>(); private idempotency = new Map<string, unknown>();
  async transaction<T>(_tenantId: string, work: (repositories: PlatformRepositories) => Promise<T>): Promise<T> { return work(this); }
  async lockScope(_scopeId: string) {}
  async appendEvent(event: EventEnvelope) { if (this.events.some(existing => existing.tenant_id === event.tenant_id && existing.event_id === event.event_id)) return false; this.events.push(structuredClone(event)); return true; }
  async getEvents(tenantId: string, incidentId?: string): Promise<EventEnvelope[]> { return this.events.filter(event => event.tenant_id === tenantId && (!incidentId || event.incident_id === incidentId)).map(event => structuredClone(event)); }
  async putEvidence() {}
  async getState(_tenantId: string, _scopeId: string) { return null; }
  async putState(incident: StoredIncident, expectedVersion: number) { if (incident.state_version !== expectedVersion && incident.state_version !== expectedVersion + 1) return false; this.states.set(`${incident.tenant_id}:${incident.scope_id}`, { version: incident.state_version, values: structuredClone(incident.values ?? {}) }); return true; }
  async putStateDiff() {}
  async linkEvidence() {}
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
  private outbox = new Map<string, OutboxMessage>();
  async enqueueOutbox(message: OutboxMessage) { const key = `${message.tenant_id}:${message.dedupe_key}`; if ([...this.outbox.values()].some(item => `${item.tenant_id}:${item.dedupe_key}` === key)) return false; this.outbox.set(`${message.tenant_id}:${message.outbox_id}`, { ...structuredClone(message), status: 'PENDING', attempts: 0 }); return true; }
  async claimOutbox(tenantId: string, workerId: string, leaseMs = 30000) { const now = Date.now(); const item = [...this.outbox.values()].find(candidate => candidate.tenant_id === tenantId && (candidate.status === 'PENDING' || (candidate.status === 'PROCESSING' && candidate.lease_expires_at && Date.parse(candidate.lease_expires_at) <= now)) && (!candidate.available_at || Date.parse(candidate.available_at) <= now)); if (!item) return null; item.status = 'PROCESSING'; item.worker_id = workerId; item.lease_expires_at = new Date(now + leaseMs).toISOString(); item.attempts = (item.attempts ?? 0) + 1; return structuredClone(item); }
  async completeOutbox(tenantId: string, outboxId: string) { const item = this.outbox.get(`${tenantId}:${outboxId}`); if (item) item.status = 'COMPLETED'; }
  async retryOutbox(tenantId: string, outboxId: string, error: string, maxAttempts = 5, delayMs?: number) { const item = this.outbox.get(`${tenantId}:${outboxId}`); if (!item) return 'DEAD_LETTER' as const; item.last_error = error; item.lease_expires_at = undefined; if ((item.attempts ?? 0) >= maxAttempts) { item.status = 'DEAD_LETTER'; return 'DEAD_LETTER' as const; } item.status = 'PENDING'; item.available_at = new Date(Date.now() + (delayMs ?? 250 * 2 ** Math.max(0, (item.attempts ?? 1) - 1))).toISOString(); return 'RETRYING' as const; }
  async getOutboxMetrics(tenantId: string) { const items = [...this.outbox.values()].filter(item => item.tenant_id === tenantId); const pending = items.filter(item => item.status === 'PENDING').length; const processing = items.filter(item => item.status === 'PROCESSING').length; const completed = items.filter(item => item.status === 'COMPLETED').length; const dead_letter = items.filter(item => item.status === 'DEAD_LETTER').length; const oldest = items.filter(item => item.status === 'PENDING').map(item => Date.parse(item.available_at ?? new Date().toISOString())).sort((a, b) => a - b)[0]; return { pending, processing, completed, dead_letter, oldest_age_ms: oldest ? Math.max(0, Date.now() - oldest) : null, retries: items.reduce((sum, item) => sum + Math.max(0, (item.attempts ?? 0) - 1), 0) }; }
  async requeueOutbox(tenantId: string, outboxId: string) { const item = this.outbox.get(`${tenantId}:${outboxId}`); if (!item || item.status !== 'DEAD_LETTER') return false; item.status = 'PENDING'; item.available_at = new Date().toISOString(); item.lease_expires_at = undefined; return true; }
  async getActorMembership(_tenantId: string, _actorId: string, _role: string) { return { active: true, facility_scope: '*', mandate_expires_at: '2099-01-01T00:00:00Z', financial_limit: 10000 }; }
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
  async lockScope(scopeId: string) { await this.db.query('SELECT pg_advisory_xact_lock(hashtextextended($1, 0))', [scopeId]); }
  async appendEvent(event: EventEnvelope) { const result = await this.db.query('INSERT INTO journal_events (tenant_id,event_id,event_type,payload,recorded_at) VALUES ($1,$2,$3,$4,$5) ON CONFLICT (tenant_id,event_id) DO NOTHING RETURNING event_id', [event.tenant_id, event.event_id, event.event_type, JSON.stringify(event), event.recorded_at]); return result.rows.length === 1; }
  async getEvents(tenantId: string, incidentId?: string) { const result = await this.db.query<EventEnvelope>('SELECT payload FROM journal_events WHERE tenant_id=$1 AND ($2::text IS NULL OR payload->>\'incident_id\'=$2) ORDER BY recorded_at,event_id', [tenantId, incidentId ?? null]); return result.rows.map(row => (row as unknown as { payload: EventEnvelope }).payload); }
  async putEvidence(record: EvidenceRecord & { tenant_id: string }) { await this.db.query('INSERT INTO evidence_records (tenant_id,evidence_id,payload) VALUES ($1,$2,$3) ON CONFLICT (tenant_id,evidence_id) DO NOTHING', [record.tenant_id, record.evidence_id, JSON.stringify(record)]); }
  async getState(tenantId: string, scopeId: string) { const result = await this.db.query<{ version: number; values: Record<string, unknown> }>('SELECT version,values FROM state_snapshots WHERE tenant_id=$1 AND scope_id=$2', [tenantId, scopeId]); return result.rows[0] ?? null; }
  async putState(incident: StoredIncident, expectedVersion: number) {
    if (incident.state_version !== expectedVersion + 1) return false;
    const updated = await this.db.query('UPDATE state_snapshots SET version=$3::bigint, values=$5::jsonb, state_hash=$6 WHERE tenant_id=$1 AND scope_id=$2 AND version=$4::bigint RETURNING scope_id', [incident.tenant_id, incident.scope_id, incident.state_version, expectedVersion, JSON.stringify(incident.values ?? {}), incident.state_hash ?? '']);
    if (updated.rows.length === 1) return true;
    const inserted = await this.db.query('INSERT INTO state_snapshots (tenant_id,scope_id,version,values,state_hash) VALUES ($1,$2,$3::bigint,$4::jsonb,$5) ON CONFLICT (tenant_id,scope_id) DO NOTHING RETURNING scope_id', [incident.tenant_id, incident.scope_id, incident.state_version, JSON.stringify(incident.values ?? {}), incident.state_hash ?? '']);
    return inserted.rows.length === 1;
  }
  async putStateDiff(diff: StateDiff) { await this.db.query('INSERT INTO state_diffs (tenant_id,scope_id,version,diff,state_hash) VALUES ($1,$2,$3,$4,$5) ON CONFLICT DO NOTHING', [diff.tenant_id, diff.scope_id, diff.version, JSON.stringify(diff.diff), diff.state_hash]); }
  async linkEvidence(relationship: EvidenceRelationship) { await this.db.query('INSERT INTO evidence_relationships (tenant_id,relationship_id,event_id,evidence_id,relationship_type) VALUES ($1,$2,$3,$4,$5) ON CONFLICT DO NOTHING', [relationship.tenant_id, relationship.relationship_id, relationship.event_id, relationship.evidence_id, relationship.relationship_type]); }
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
  async enqueueOutbox(message: OutboxMessage) { const result = await this.db.query('INSERT INTO transactional_outbox (tenant_id,outbox_id,dedupe_key,topic,aggregate_id,payload,correlation_id,trace_id,state_version) VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9) ON CONFLICT (tenant_id,dedupe_key) DO NOTHING RETURNING outbox_id', [message.tenant_id, message.outbox_id, message.dedupe_key, message.topic, message.aggregate_id, JSON.stringify(message.payload), message.correlation_id, message.trace_id, message.state_version ?? null]); return result.rows.length === 1; }
  async claimOutbox(tenantId: string, workerId: string, leaseMs = 30000) { const result = await this.db.query<OutboxMessage & { payload: Record<string, unknown> }>(`UPDATE transactional_outbox SET status='PROCESSING', attempts=attempts+1, locked_at=now(), lease_expires_at=now() + ($3::integer * interval '1 millisecond'), worker_id=$2 WHERE tenant_id=$1 AND outbox_id=(SELECT outbox_id FROM transactional_outbox WHERE tenant_id=$1 AND available_at<=now() AND (status='PENDING' OR (status='PROCESSING' AND lease_expires_at<=now())) ORDER BY created_at FOR UPDATE SKIP LOCKED LIMIT 1) RETURNING *`, [tenantId, workerId, leaseMs]); if (!result.rows[0]) return null; return { ...result.rows[0], status: 'PROCESSING' as const, attempts: result.rows[0].attempts, payload: result.rows[0].payload }; }
  async completeOutbox(tenantId: string, outboxId: string) { await this.db.query("UPDATE transactional_outbox SET status='COMPLETED', completed_at=now(), lease_expires_at=NULL WHERE tenant_id=$1 AND outbox_id=$2 AND status='PROCESSING'", [tenantId, outboxId]); }
  async retryOutbox(tenantId: string, outboxId: string, error: string, maxAttempts = 5, delayMs?: number) { const result = await this.db.query<{ attempts: number }>('SELECT attempts FROM transactional_outbox WHERE tenant_id=$1 AND outbox_id=$2', [tenantId, outboxId]); const attempts = Number(result.rows[0]?.attempts ?? maxAttempts); const dead = attempts >= maxAttempts; await this.db.query(`UPDATE transactional_outbox SET status=$3, available_at=now() + ($4::integer * interval '1 millisecond'), lease_expires_at=NULL, last_error=$5, last_error_code=$6, last_error_metadata=$7::jsonb WHERE tenant_id=$1 AND outbox_id=$2`, [tenantId, outboxId, dead ? 'DEAD_LETTER' : 'PENDING', dead ? 0 : (delayMs ?? 250 * 2 ** Math.max(0, attempts - 1)), error.slice(0, 1000), dead ? 'WORKER_EXHAUSTED' : 'WORKER_RETRY', JSON.stringify({ attempts, max_attempts: maxAttempts })]); return dead ? 'DEAD_LETTER' as const : 'RETRYING' as const; }
  async getOutboxMetrics(tenantId: string) { const result = await this.db.query<{ pending: string; processing: string; completed: string; dead_letter: string; oldest_age_ms: string | null; retries: string }>(`SELECT count(*) FILTER (WHERE status='PENDING') pending, count(*) FILTER (WHERE status='PROCESSING') processing, count(*) FILTER (WHERE status='COMPLETED') completed, count(*) FILTER (WHERE status='DEAD_LETTER') dead_letter, EXTRACT(EPOCH FROM (now()-min(created_at) FILTER (WHERE status='PENDING')))*1000 oldest_age_ms, coalesce(sum(GREATEST(attempts-1,0)),0) retries FROM transactional_outbox WHERE tenant_id=$1`, [tenantId]); const row = result.rows[0]; return { pending: Number(row?.pending ?? 0), processing: Number(row?.processing ?? 0), completed: Number(row?.completed ?? 0), dead_letter: Number(row?.dead_letter ?? 0), oldest_age_ms: row?.oldest_age_ms == null ? null : Number(row.oldest_age_ms), retries: Number(row?.retries ?? 0) }; }
  async requeueOutbox(tenantId: string, outboxId: string) { const result = await this.db.query("UPDATE transactional_outbox SET status='PENDING', available_at=now(), lease_expires_at=NULL, last_error_code='GOVERNED_REQUEUE' WHERE tenant_id=$1 AND outbox_id=$2 AND status='DEAD_LETTER' RETURNING outbox_id", [tenantId, outboxId]); return result.rows.length === 1; }
  async getActorMembership(tenantId: string, actorId: string, role: string) { const result = await this.db.query<{ active: boolean; facility_scope: string | null; mandate_expires_at: string | null; financial_limit: number | null }>('SELECT active,facility_scope,mandate_expires_at,financial_limit FROM actor_memberships WHERE tenant_id=$1 AND actor_id=$2 AND role=$3', [tenantId, actorId, role]); return result.rows[0] ?? null; }
}


