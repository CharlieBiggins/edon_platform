import type { ActionProposal, DecisionReceipt, KernelDecision, OutcomeRecord } from '../../contracts/src/index.js';
const receiptHash = (value: unknown) => {
  const text = JSON.stringify(value);
  let hash = 2166136261;
  for (let i = 0; i < text.length; i++) hash = Math.imul(hash ^ text.charCodeAt(i), 16777619);
  return `sha256:sim-${(hash >>> 0).toString(16)}`;
};
export class HashLinkedReceiptService {
  issue(proposal: ActionProposal, decision: KernelDecision, outcome: OutcomeRecord) {
    const body = { receipt_id: `RCP-${proposal.proposal_id}`, incident_id: proposal.incident_id, proposal_id: proposal.proposal_id, kernel_decision_id: decision.decision_id, human_reviewed: Boolean(decision.review_id), shadow_only: true as const, outcome_id: outcome.outcome_id, event_ids: ['evt-19001', 'evt-19002', 'evt-19003', 'evt-19004', 'evt-19005', 'evt-19006'], proposal_hash: proposal.proposal_hash, state_version: proposal.context?.state_version ?? proposal.state_version, evidence_versions: proposal.context?.evidence_versions, model_release: proposal.context?.c1_release, policy_version: proposal.context?.policy_version ?? proposal.policy_version, authority_version: proposal.context?.authority_version, simulated: true as const };
    return { ...body, receipt_hash: receiptHash(body), signature: '', signature_status: 'SIGNATURE_PENDING' } satisfies DecisionReceipt;
  }
  verify(receipt: DecisionReceipt) { const { receipt_hash, signature, signature_status, digest, algorithm, key_id, key_version, signed_at, ...body } = receipt; return receipt_hash === receiptHash(body) && (signature_status === 'SIGNATURE_PENDING' || Boolean(signature && digest && algorithm && key_id && key_version && signed_at)); }
}


