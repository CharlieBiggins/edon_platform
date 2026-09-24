import { runCapacityDisruptionScenario } from './scenario-runner';
import { AppendOnlyJournal } from '../../platform-core/src/event-journal';
import { DeterministicEvidenceAdmission } from '../../platform-core/src/evidence-admission';
import { DeterministicKernel } from '../../platform-core/src/kernel';
import { HumanReviewGate } from '../../platform-core/src/human-review';
import { HashLinkedReceiptService } from '../../platform-core/src/receipt-service';
import { classifyAcknowledgement } from '../../platform-core/src/outcome-comparator';
import { ReplayableStateProjector } from '../../platform-core/src/state-projector';

export type SliceCheck = { name: string; passed: boolean; detail: string };

/** Executable, deterministic acceptance checks for the local reference slice. */
export function validateReferenceSlice(): SliceCheck[] {
  const first = runCapacityDisruptionScenario();
  const second = runCapacityDisruptionScenario();
  const firstState = JSON.stringify(first.state);
  const secondState = JSON.stringify(second.state);
  const firstReceipt = JSON.stringify(first.receipt);
  const secondReceipt = JSON.stringify(second.receipt);
  const duplicateJournal = new AppendOnlyJournal();
  const event = first.journal.all()[0];
  const firstAppend = duplicateJournal.append(event);
  const duplicateAppend = duplicateJournal.append(event);
  const tampered = first.journal.all()[0] as { payload: { capacity_units?: number } };
  const originalCapacity = tampered.payload.capacity_units;
  tampered.payload.capacity_units = 999;
  const tamperDetected = !first.journal.verifyIntegrity();
  tampered.payload.capacity_units = originalCapacity;
  const invalidEvidence = new DeterministicEvidenceAdmission().admit({ event: 'capacity_disruption', trusted_source: false });
  const staleDecision = new DeterministicKernel().evaluateAt(first.proposal, 143, 30000);
  const overMandateDecision = new DeterministicKernel().evaluateAt(first.proposal, 142, 1000);
  const reevaluated = new HumanReviewGate().reevaluate(first.proposal, true, 142, 30000);
  const reversedState = new ReplayableStateProjector().project([...first.journal.all()].reverse());
  const invalidProjection = new ReplayableStateProjector().project([{ event_type: 'STATE_PROJECTED', state_version_after: 999, payload: { capacity_units: 'not-a-number', commitments_at_risk: 99 }, occurred_at: '2026-09-24T15:30:00Z' }]);
  const receiptService = new HashLinkedReceiptService();
  const tamperedReceipt = { ...first.receipt, event_ids: [...first.receipt.event_ids, 'evt-tampered'] };
  return [
    { name: 'deterministic replay', passed: firstState === secondState && firstReceipt === secondReceipt, detail: 'Same fixed scenario produces the same state and receipt.' },
    { name: 'state transition', passed: first.state.version === 142, detail: 'Capacity disruption projects state v141 to v142.' },
    { name: 'typed proposal citations', passed: first.proposal.citations.includes('EV-2081') && first.proposal.citations.includes('EV-2085'), detail: 'Proposal retains resolvable evidence references, including missing evidence.' },
    { name: 'independent Kernel review', passed: first.decision.disposition === 'APPROVAL_REQUIRED' && first.decision.required_approval, detail: 'Kernel requires approval for the bounded proposal.' },
    { name: 'human reevaluation boundary', passed: first.humanReview.approved && first.humanReview.reevaluation_required, detail: 'Human approval is recorded as input; reevaluation remains required.' },
    { name: 'shadow isolation', passed: first.shadow.executed === false && first.shadow.credentials === 'NONE', detail: 'Shadow evaluation has no dispatch path or customer credentials.' },
    { name: 'value separation', passed: first.comparison.estimated_cost !== first.comparison.observed_cost && first.outcome.verification_status === 'PENDING', detail: 'Modeled and observed value remain separate pending verification.' },
    { name: 'reconstruction completeness', passed: first.receipt.event_ids.length >= 2 && first.receipt.shadow_only, detail: 'Receipt retains the lifecycle event references and shadow boundary.' },
    { name: 'duplicate events are idempotent', passed: firstAppend && !duplicateAppend && duplicateJournal.all().length === 1, detail: 'A repeated event ID is ignored.' },
    { name: 'invalid evidence cannot project state', passed: invalidEvidence.length === 0, detail: 'Untrusted evidence is rejected before projection.' },
    { name: 'invalid state payload cannot project state', passed: invalidProjection.version === 141, detail: 'Malformed state updates are ignored by the deterministic projector.' },
    { name: 'stale state invalidates proposal', passed: staleDecision.disposition === 'DENY' && staleDecision.reason_codes.includes('STALE_STATE_VERSION'), detail: 'Kernel denies a proposal evaluated against a stale state version.' },
    { name: 'out-of-order events preserve history', passed: reversedState.version === 142, detail: 'Replay orders registered event timestamps before projecting state.' },
    { name: 'mandate boundary is enforced', passed: overMandateDecision.disposition === 'DENY', detail: 'Approval outside the reviewer mandate is denied.' },
    { name: 'human approval cannot bypass reevaluation', passed: reevaluated.state_version === 142 && reevaluated.disposition === 'APPROVAL_REQUIRED', detail: 'Approval returns to the Kernel for an independent reevaluation.' },
    { name: 'journal tampering is detectable', passed: tamperDetected, detail: 'Mutating an appended record breaks journal integrity verification.' },
    { name: 'receipt tampering is detectable', passed: !receiptService.verify(tamperedReceipt), detail: 'Changing receipt content invalidates its deterministic hash.' },
    { name: 'missing acknowledgement is explicit', passed: classifyAcknowledgement(false, false) === 'OUTCOME_UNKNOWN' && classifyAcknowledgement(false, true) === 'RECONCILIATION_REQUIRED', detail: 'Unknown and reconciliation-required outcomes remain distinct.' },
  ];
}
