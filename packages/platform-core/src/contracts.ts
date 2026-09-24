export * from '../../contracts/src/index.js';
export interface PlatformClock { now(): string; }
export interface EventJournal { append<T>(event: import('../../contracts/src/index.js').EventEnvelope<T>): boolean; all(): import('../../contracts/src/index.js').EventEnvelope<unknown>[]; }
export interface EvidenceAdmission { admit(input: unknown): import('../../contracts/src/index.js').EvidenceRecord[]; }
export interface StateProjector { project(events: import('../../contracts/src/index.js').EventEnvelope<unknown>[]): { version: number; values: Record<string, unknown> }; }
export interface ProposalGenerator { create(state: { version: number; values: Record<string, unknown> }, evidence: import('../../contracts/src/index.js').EvidenceRecord[]): import('../../contracts/src/index.js').ActionProposal; }
export interface Kernel { evaluate(proposal: import('../../contracts/src/index.js').ActionProposal): import('../../contracts/src/index.js').KernelDecision; }


