import { createHash } from 'node:crypto';
import type { EventEnvelope } from '../../contracts/src/index.js';
import type { PlatformRepositories, InstitutionReleaseRecord } from './repositories.js';
import { assertInstitutionTransition, type InstitutionGate, type InstitutionReleaseState } from './institution-release.js';

export type InstitutionTransitionActorType = 'HUMAN' | 'WORKER' | 'SYSTEM';
export type TransitionFaultPoint = 'AFTER_CAS' | 'AFTER_JOURNAL_APPEND' | 'AFTER_OUTBOX_ENQUEUE';
export interface TransitionFaultInjector { failAt(point: TransitionFaultPoint): Promise<void> | void; }

export type InstitutionReleaseTransitionRequest = {
  tenant_id: string;
  institution_id: string;
  release_id: string;
  expected_state: InstitutionReleaseState;
  expected_version: number;
  next_state: InstitutionReleaseState;
  actor_id: string;
  actor_type: InstitutionTransitionActorType;
  reason: string;
  correlation_id: string;
  trace_id: string;
  idempotency_key: string;
  occurred_at: string;
  gate?: InstitutionGate;
};

export type InstitutionReleaseTransitionResult = {
  tenant_id: string;
  institution_id: string;
  release_id: string;
  previous_state: InstitutionReleaseState;
  next_state: InstitutionReleaseState;
  previous_version: number;
  next_version: number;
  actor_id: string;
  actor_type: InstitutionTransitionActorType;
  reason: string;
  correlation_id: string;
  trace_id: string;
  idempotency_key: string;
  occurred_at: string;
  release_manifest_hash: string;
  event_id: string;
  outbox_id: string;
};

const canonicalize = (value: unknown): string => {
  if (value === null || typeof value !== 'object') return JSON.stringify(value);
  if (Array.isArray(value)) return `[${value.map(canonicalize).join(',')}]`;
  return `{${Object.entries(value as Record<string, unknown>).sort(([a], [b]) => a.localeCompare(b)).map(([key, item]) => `${JSON.stringify(key)}:${canonicalize(item)}`).join(',')}}`;
};
const hash = (value: unknown) => `sha256:${createHash('sha256').update(canonicalize(value)).digest('hex')}`;

/** The only service allowed to mutate a release lifecycle state. */
export class GovernedInstitutionTransitionService {
  constructor(private readonly repositories: PlatformRepositories, private readonly faultInjector?: TransitionFaultInjector) {}

  async transition(request: InstitutionReleaseTransitionRequest): Promise<InstitutionReleaseTransitionResult> {
    if (!request.idempotency_key) throw new Error('IDEMPOTENCY_KEY_REQUIRED');
    return this.repositories.transaction(request.tenant_id, async (repositories) => {
      const operationKey = `institution-release-transition:${request.release_id}:${request.idempotency_key}`;
      const existing = await repositories.getIdempotency(request.tenant_id, operationKey);
      if (existing) return existing as InstitutionReleaseTransitionResult;
      const claim = await repositories.claimIdempotency(request.tenant_id, operationKey, { status: 'PROCESSING' });
      if (!claim.claimed) {
        if (claim.response && typeof claim.response === 'object' && 'status' in claim.response && (claim.response as { status?: string }).status === 'PROCESSING') throw new Error('DUPLICATE_IN_FLIGHT');
        return claim.response as InstitutionReleaseTransitionResult;
      }

      const release = await repositories.getInstitutionRelease(request.tenant_id, request.release_id);
      if (!release || release.institution_id !== request.institution_id) throw new Error('RELEASE_NOT_FOUND');
      if (!release.manifest_hash) throw new Error('RELEASE_MANIFEST_INVALID');

      assertInstitutionTransition(
        release.lifecycle_state as InstitutionReleaseState,
        request.next_state,
        request.gate ?? {
          broken_references: 0, conflicting_policies: 0, missing_resource_ownership: 0,
          ambiguous_authority: 0, invalid_mandates: 0, unsupported_workflow_transitions: 0,
          unversioned_sources: 0, unqualified_simulations: 0,
        },
        request.expected_version,
        release.version,
      );
      if (release.lifecycle_state !== request.expected_state) throw new Error('STATE_STALE');

      const nextVersion = request.expected_version + 1;
      const eventId = `institution-release-transition:${request.release_id}:v${nextVersion}`;
      const outboxId = `institution-release-transition:${request.release_id}:v${nextVersion}`;
      const recordedAt = new Date().toISOString();
      const priorEvents = await repositories.getEvents(request.tenant_id);
      const result: InstitutionReleaseTransitionResult = {
        tenant_id: request.tenant_id, institution_id: request.institution_id, release_id: request.release_id,
        previous_state: request.expected_state, next_state: request.next_state,
        previous_version: request.expected_version, next_version: nextVersion,
        actor_id: request.actor_id, actor_type: request.actor_type, reason: request.reason,
        correlation_id: request.correlation_id, trace_id: request.trace_id,
        idempotency_key: request.idempotency_key, occurred_at: request.occurred_at,
        release_manifest_hash: release.manifest_hash, event_id: eventId, outbox_id: outboxId,
      };

      const updated = await repositories.transitionInstitutionRelease(
        request.tenant_id, request.release_id, request.expected_state, request.expected_version,
        request.next_state, request.correlation_id, request.trace_id, release.payload,
      );
      if (!updated) throw new Error('STATE_STALE');
      await this.faultInjector?.failAt('AFTER_CAS');

      const eventPayload = { ...result };
      const event: EventEnvelope<typeof eventPayload> = {
        event_id: eventId, tenant_id: request.tenant_id, event_type: 'INSTITUTION_RELEASE_TRANSITIONED',
        actor_id: request.actor_id, actor_type: request.actor_type === 'WORKER' ? 'WORKER' : request.actor_type,
        scope_id: request.institution_id, incident_id: request.release_id,
        occurred_at: request.occurred_at, observed_at: request.occurred_at,
        available_to_controller_at: recordedAt, recorded_at: recordedAt,
        correlation_id: request.correlation_id, trace_id: request.trace_id,
        state_version_before: request.expected_version, state_version_after: nextVersion,
        policy_version: 'INSTITUTION-COMPILER-v1', payload: eventPayload,
        payload_hash: hash(eventPayload), previous_record_hash: priorEvents.at(-1)?.payload_hash ?? 'sha256:genesis',
        signature: 'pending', simulated: true,
      };
      if (!await repositories.appendEvent(event)) throw new Error('JOURNAL_WRITE_FAILED');
      await this.faultInjector?.failAt('AFTER_JOURNAL_APPEND');
      if (!await repositories.enqueueOutbox({
        outbox_id: outboxId, tenant_id: request.tenant_id,
        dedupe_key: `institution-release:${request.release_id}:${request.next_state}:v${nextVersion}`,
        topic: `INSTITUTION_RELEASE_${request.next_state}`, aggregate_id: request.release_id,
        payload: eventPayload, correlation_id: request.correlation_id, trace_id: request.trace_id,
        state_version: nextVersion,
      })) throw new Error('OUTBOX_WRITE_FAILED');
      await this.faultInjector?.failAt('AFTER_OUTBOX_ENQUEUE');

      await repositories.putIdempotencyResponse(request.tenant_id, operationKey, result);
      return result;
    });
  }
}
