import type { ActionProposal } from '../../contracts/src';
export class ShadowEvaluator { record(proposal: ActionProposal) { return { proposal_id: proposal.proposal_id, executed: false as const, recommendation_recorded_at: '2026-09-24T15:42:04.108Z', credentials: 'NONE' as const, status: 'SHADOW_ONLY' as const }; } }
