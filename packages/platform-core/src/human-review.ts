import type { ActionProposal, KernelDecision } from '../../contracts/src/index.js';
import { DeterministicKernel } from './kernel.js';

export class HumanReviewGate {
  reevaluate(proposal: ActionProposal, approved: boolean, currentStateVersion: number, mandateLimit: number): KernelDecision {
    return new DeterministicKernel().evaluateAt(proposal, currentStateVersion, mandateLimit, { approved, review_id: `review-${proposal.proposal_id}` });
  }
}


