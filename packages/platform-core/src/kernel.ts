import type { Kernel } from './contracts.js';
export class DeterministicKernel implements Kernel {
  evaluate(proposal: Parameters<Kernel['evaluate']>[0]) {
    return this.evaluateAt(proposal, proposal.state_version, 30000);
  }
  evaluateAt(proposal: Parameters<Kernel['evaluate']>[0], currentStateVersion: number, mandateLimit: number, review?: { approved: boolean; review_id: string }) {
    const stale = proposal.state_version !== currentStateVersion;
    const overMandate = proposal.modeled_cost > mandateLimit;
    const modelInvalid = proposal.assumptions.some(assumption => assumption === 'MODEL_TIMEOUT' || assumption === 'MODEL_OUTPUT_INVALID');
    const reasons = [...(stale ? ['STALE_STATE_VERSION'] : []), ...(modelInvalid ? ['MODEL_UNAVAILABLE_OR_INVALID'] : []), ...(overMandate ? ['COST_EXCEEDS_MANDATE'] : []), 'MISSING_CARRIER_EVIDENCE'];
    const disposition = stale || modelInvalid ? 'ABSTAIN' as const : review ? (!review.approved ? 'REVISE' as const : overMandate ? 'DENY' as const : 'ALLOW' as const) : 'APPROVAL_REQUIRED' as const;
    return { decision_id: `DEC-${proposal.proposal_id}-${review?.review_id ?? 'initial'}`, proposal_id: proposal.proposal_id, disposition, reason_codes: reasons, required_approval: disposition === 'APPROVAL_REQUIRED', evaluated_at: new Date(0).toISOString(), state_version: currentStateVersion, policy_version: proposal.policy_version, proposal_hash: proposal.proposal_hash, review_id: review?.review_id, simulated: true as const };
  }
}


