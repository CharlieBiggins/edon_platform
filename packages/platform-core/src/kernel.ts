import type { Kernel } from './contracts.js';
export class DeterministicKernel implements Kernel {
  evaluate(proposal: Parameters<Kernel['evaluate']>[0]) {
    return this.evaluateAt(proposal, proposal.state_version, 30000);
  }
  evaluateAt(proposal: Parameters<Kernel['evaluate']>[0], currentStateVersion: number, mandateLimit: number) {
    const stale = proposal.state_version !== currentStateVersion;
    const overMandate = proposal.modeled_cost > mandateLimit;
    const reasons = [
      ...(stale ? ['STALE_STATE_VERSION'] : []),
      ...(overMandate ? ['COST_EXCEEDS_REVIEWER_MANDATE'] : []),
      'MISSING_CARRIER_EVIDENCE',
    ];
    return { decision_id: 'DEC-1042', proposal_id: proposal.proposal_id,
      disposition: stale || overMandate ? 'DENY' as const : 'APPROVAL_REQUIRED' as const,
      reason_codes: reasons, required_approval: !stale && !overMandate,
      evaluated_at: '2026-09-24T15:42:03.122Z', state_version: currentStateVersion,
      policy_version: proposal.policy_version, simulated: true as const };
  }
}


