export type ActorType = 'HUMAN' | 'AGENT' | 'SYSTEM' | 'KERNEL' | 'CONNECTOR';
export type LifecycleEvent = 'OBSERVATION_RECEIVED' | 'EVIDENCE_ADMITTED' | 'STATE_PROJECTED' | 'MODEL_INVOKED' | 'PROPOSAL_CREATED' | 'KERNEL_DECIDED' | 'HUMAN_REVIEWED' | 'SHADOW_RECOMMENDATION_RECORDED' | 'OUTCOME_OBSERVED' | 'OUTCOME_VERIFIED' | 'RECEIPT_ISSUED' | 'CORRECTION_RECORDED';
export type KernelDisposition = 'ALLOW' | 'DENY' | 'ABSTAIN' | 'ESCALATE' | 'REVISE' | 'REASSIGN' | 'APPROVAL_REQUIRED';

export interface EventEnvelope<T = Record<string, unknown>> {
  event_id: string; tenant_id: string; event_type: LifecycleEvent; actor_id: string; actor_type: ActorType;
  scope_id: string; incident_id: string; occurred_at: string; observed_at: string; available_to_controller_at: string; recorded_at: string;
  correlation_id: string; causation_id?: string; trace_id: string; state_version_before: number; state_version_after: number;
  policy_version: string; model_release?: string; payload: T; payload_hash: string; previous_record_hash: string; signature: string; simulated: true;
}
export interface EvidenceRecord { evidence_id: string; status: 'verified' | 'observed' | 'reported' | 'inferred' | 'missing' | 'restricted'; source: string; version: string; citation_text: string; }
export interface ActionProposal { proposal_id: string; incident_id: string; objective: string; actions: string[]; modeled_cost: number; commitments_protected: number; assumptions: string[]; citations: string[]; state_version: number; policy_version: string; status: 'DRAFT' | 'PENDING_KERNEL' | 'REVIEW_REQUIRED' | 'SHADOW_RECORDED'; }
export interface KernelDecision { decision_id: string; proposal_id: string; disposition: KernelDisposition; reason_codes: string[]; required_approval: boolean; evaluated_at: string; state_version: number; policy_version: string; simulated: true; }
export interface OutcomeRecord { outcome_id: string; proposal_id: string; observed_at: string; recovery_time: string; actual_cost: number; commitments_protected: number; evidence_ids: string[]; verification_status: 'PENDING' | 'VERIFIED' | 'DISPUTED'; }
export interface DecisionReceipt { receipt_id: string; incident_id: string; proposal_id: string; kernel_decision_id: string; human_reviewed: boolean; shadow_only: true; outcome_id?: string; event_ids: string[]; receipt_hash: string; signature: string; simulated: true; }
export type C1CapabilityStatus = 'INTENDED' | 'EXPERIMENTAL' | 'RESEARCH_SUPPORTED' | 'QUALIFIED_SHADOW' | 'QUALIFIED_ASSISTED' | 'QUALIFIED_PRODUCTION' | 'SUSPENDED' | 'RETIRED';
export interface C1CapabilityManifest { capability_id: string; name: string; description: string; release_id: string; model_hash: string; adapter_hash: string; actionnet_version: string; qualification_status: C1CapabilityStatus; qualified_workflows: string[]; permitted_operating_modes: string[]; input_schema: string; output_schema: string; required_context: string[]; evaluation_ids: string[]; evaluation_results: Record<string, unknown>; safety_constraints: string[]; unsupported_conditions: string[]; latency_limit_ms: number; cost_limit: string; fallback_behavior: string; approval_authority: string; qualified_at: string; expires_at: string; }
export interface C1ModelRelease { release_id: string; model_hash: string; adapter_hash: string; actionnet_version: string; status: C1CapabilityStatus; capabilities: C1CapabilityManifest[]; }
export * from './api.js';
