export const INSTITUTION_RELEASE_STATES = ['DRAFT', 'EXTRACTED', 'MAPPED', 'VALIDATED', 'QUALIFIED', 'APPROVED', 'SIGNED', 'SHADOW', 'ACTIVE', 'REJECTED', 'SUPERSEDED', 'ROLLED_BACK'] as const;
export type InstitutionReleaseState = typeof INSTITUTION_RELEASE_STATES[number];

const transitions: Record<InstitutionReleaseState, InstitutionReleaseState[]> = {
  DRAFT: ['EXTRACTED', 'REJECTED'], EXTRACTED: ['MAPPED', 'REJECTED'], MAPPED: ['VALIDATED', 'REJECTED'], VALIDATED: ['QUALIFIED', 'REJECTED'],
  QUALIFIED: ['APPROVED', 'REJECTED'], APPROVED: ['SIGNED', 'REJECTED'], SIGNED: ['SHADOW', 'SUPERSEDED', 'ROLLED_BACK'], SHADOW: ['ACTIVE', 'SUPERSEDED', 'ROLLED_BACK'], ACTIVE: ['SUPERSEDED', 'ROLLED_BACK'],
  REJECTED: [], SUPERSEDED: [], ROLLED_BACK: [],
};

export type InstitutionGate = { broken_references: number; conflicting_policies: number; missing_resource_ownership: number; ambiguous_authority: number; invalid_mandates: number; unsupported_workflow_transitions: number; unversioned_sources: number; unqualified_simulations: number };
export type InstitutionTransition = { release_id: string; tenant_id: string; from: InstitutionReleaseState; to: InstitutionReleaseState; actor_id: string; occurred_at: string; reason: string; expected_version: number; version: number };

export function assertInstitutionTransition(current: InstitutionReleaseState, next: InstitutionReleaseState, gate: InstitutionGate, expectedVersion: number, actualVersion: number) {
  if (expectedVersion !== actualVersion) throw new Error('STATE_STALE');
  if (!transitions[current].includes(next)) throw new Error(`INVALID_INSTITUTION_TRANSITION:${current}->${next}`);
  if (['VALIDATED', 'QUALIFIED', 'APPROVED', 'SIGNED', 'SHADOW', 'ACTIVE'].includes(next)) {
    const blockers = Object.entries(gate).filter(([, value]) => value > 0).map(([key]) => key);
    if (blockers.length) throw new Error(`INSTITUTION_GATE_BLOCKED:${blockers.join(',')}`);
  }
  return true;
}

export function transitionInstitutionRelease(input: { release_id: string; tenant_id: string; current: InstitutionReleaseState; next: InstitutionReleaseState; actor_id: string; occurred_at: string; reason: string; expected_version: number; actual_version: number; gate: InstitutionGate }): InstitutionTransition {
  assertInstitutionTransition(input.current, input.next, input.gate, input.expected_version, input.actual_version);
  return { release_id: input.release_id, tenant_id: input.tenant_id, from: input.current, to: input.next, actor_id: input.actor_id, occurred_at: input.occurred_at, reason: input.reason, expected_version: input.expected_version, version: input.actual_version + 1 };
}

export function canDeployInstitutionRelease(state: InstitutionReleaseState, signatureStatus: 'SIGNATURE_PENDING' | 'SIGNED', qualificationStatus: InstitutionReleaseState) {
  if (signatureStatus !== 'SIGNED') throw new Error('SIGNATURE_PENDING');
  if (qualificationStatus !== 'QUALIFIED') throw new Error('RELEASE_NOT_QUALIFIED');
  if (!['SIGNED', 'SHADOW'].includes(state)) throw new Error('RELEASE_NOT_DEPLOYABLE');
  return true;
}
