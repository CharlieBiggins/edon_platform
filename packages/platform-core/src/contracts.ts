export * from '../../contracts/src';
export interface PlatformClock { now(): string; }
export interface EventJournal { append<T>(event: import('../../contracts/src').EventEnvelope<T>): boolean; all(): import('../../contracts/src').EventEnvelope<unknown>[]; }
export interface EvidenceAdmission { admit(input: unknown): import('../../contracts/src').EvidenceRecord[]; }
export interface StateProjector { project(events: import('../../contracts/src').EventEnvelope<unknown>[]): { version: number; values: Record<string, unknown> }; }
export interface ProposalGenerator { create(state: { version: number; values: Record<string, unknown> }, evidence: import('../../contracts/src').EvidenceRecord[]): import('../../contracts/src').ActionProposal; }
export interface Kernel { evaluate(proposal: import('../../contracts/src').ActionProposal): import('../../contracts/src').KernelDecision; }
