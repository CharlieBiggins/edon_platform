export type Tone = 'teal' | 'amber' | 'red' | 'neutral' | 'blue';
export type Scenario = 'normal' | 'loading' | 'empty' | 'stale' | 'conflicted' | 'restricted' | 'degraded' | 'disconnected';
export type Role = 'Operator' | 'Approver' | 'Auditor';
export type Page = 'overview' | 'queue' | 'incident' | 'reviews' | 'outcomes' | 'receipts' | 'value' | 'state' | 'integrations' | 'settings' | 'location' | 'actor' | 'reconstructions' | 'exceptions' | 'integrity' | 'holds' | 'exports' | 'builder' | 'intelligence';
export type WorkspaceTab = 'decision' | 'evidence' | 'shadow' | 'activity';
export type ReviewStatus = 'unreviewed' | 'pending' | 'reviewed' | 'invalidated';
export interface Plan {
  id: string; name: string; kind: string; cost: number; recovery: string;
  protected: number; risk: 'Low' | 'Medium' | 'High'; feasibility: string;
  summary: string; actions: string[]; assumptions: string[]; resources: string;
}
export interface Incident {
  id: string; title: string; site: string; severity: 'Critical' | 'High' | 'Moderate';
  status: string; owner: string; initials: string; occurred: string; observed: string;
  exposure: number; orders: number; commitments: number; summary: string;
  active: boolean; decisionDeadline: string; timeRemaining: string; costOfDelay: string;
  stateFreshness: string; nextRequiredAction: string;
  plans: Plan[]; operatorAction: string; actualRecovery: string; actualCost: number;
}
export interface Evidence {
  id: string; title: string; status: 'Verified' | 'Observed' | 'Reported' | 'Inferred' | 'Disputed' | 'Missing' | 'Stale' | 'Assumption' | 'Restricted';
  source: string; owner: string; time: string; version: string; description: string;
}
export interface Activity { id: string; time: string; title: string; detail: string; tone: Tone; }
export interface Receipt {
  id: string; incidentId: string; title: string; type: string; plan: string;
  stateVersion: number; proposalVersion: number; time: string; actor: string;
  status: 'Current' | 'Superseded'; detail: string; simulated: true;
}
export interface ReviewRecord { incidentId: string; planId: string; stateVersion: number; proposalVersion: number; status: ReviewStatus; }
export interface RecourseRecord { id: string; incidentId: string; kind: string; detail: string; blocking: boolean; status: 'Open' | 'Resolved'; }
