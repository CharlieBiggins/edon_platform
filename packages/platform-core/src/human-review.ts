import type { ActionProposal, KernelDecision } from '../../contracts/src';
import { DeterministicKernel } from './kernel';

export class HumanReviewGate {
  reevaluate(proposal: ActionProposal, approved: boolean, currentStateVersion: number, mandateLimit: number): KernelDecision {
    if (!approved) return new DeterministicKernel().evaluateAt(proposal, currentStateVersion, mandateLimit);
    return new DeterministicKernel().evaluateAt(proposal, currentStateVersion, mandateLimit);
  }
}
