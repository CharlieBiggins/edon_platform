import type { ActionProposal, OutcomeRecord } from '../../contracts/src';
export class OutcomeComparator { compare(proposal: ActionProposal, outcome: OutcomeRecord) { return { proposal_id: proposal.proposal_id, estimated_commitments: proposal.commitments_protected, observed_commitments: outcome.commitments_protected, estimated_cost: proposal.modeled_cost, observed_cost: outcome.actual_cost, status: 'PENDING_VERIFICATION' as const }; } }
export const classifyAcknowledgement = (acknowledged: boolean, reconciled: boolean) =>
  acknowledged ? 'OUTCOME_OBSERVED' as const : reconciled ? 'RECONCILIATION_REQUIRED' as const : 'OUTCOME_UNKNOWN' as const;
