import { createHash } from 'node:crypto';
import type { ExecutionCommand, ExecutionStatus } from '../../contracts/src/index.js';
import type { ExecutionTransition, PlatformRepositories } from './repositories.js';

const hash = (value: unknown) => `sha256:${createHash('sha256').update(JSON.stringify(value)).digest('hex')}`;
const transitions: Record<ExecutionStatus, ExecutionStatus[]> = {
  DISPATCH_PENDING: ['DISPATCHED','DISPATCH_REJECTED','DISPATCH_FAILED','EXPIRED','CANCELLED'],
  DISPATCHED: ['ACKNOWLEDGED','OUTCOME_UNKNOWN','DISPATCH_FAILED','EXPIRED'],
  ACKNOWLEDGED: ['OUTCOME_REPORTED','OUTCOME_UNKNOWN','RECONCILIATION_REQUIRED'],
  OUTCOME_REPORTED: ['OUTCOME_VERIFIED','PARTIALLY_COMPLETED','COMPENSATION_REQUIRED','RECONCILIATION_REQUIRED'],
  OUTCOME_VERIFIED: ['COMPLETED','PARTIALLY_COMPLETED','COMPENSATION_REQUIRED'],
  COMPLETED: [], DISPATCH_REJECTED: [], DISPATCH_FAILED: [], OUTCOME_UNKNOWN: ['ACKNOWLEDGED','RECONCILIATION_REQUIRED','CANCELLED'],
  RECONCILIATION_REQUIRED: ['ACKNOWLEDGED','OUTCOME_REPORTED','PARTIALLY_COMPLETED','COMPENSATION_REQUIRED','CANCELLED'],
  PARTIALLY_COMPLETED: ['OUTCOME_VERIFIED','COMPENSATION_REQUIRED','COMPLETED'], COMPENSATION_REQUIRED: ['DISPATCH_PENDING','CANCELLED','COMPLETED'], CANCELLED: [], EXPIRED: [],
};

export type ConnectorCredentialProvider = { getCredential(scope: string, expiresAt: string): Promise<{ token: string; expiresAt: string }> };
export class ShadowExecutionAssurance {
  constructor(private readonly repositories: PlatformRepositories) {}
  async create(command: Omit<ExecutionCommand, 'status'|'command_hash'> & { tenant_id: string }): Promise<ExecutionCommand & { tenant_id: string }> {
    const value = { ...command, status: 'DISPATCH_PENDING' as const };
    const result = { ...value, command_hash: hash(value) };
    await this.repositories.putExecution(result);
    await this.transition(result, null, 'DISPATCH_PENDING', { reason: 'shadow_mode_pending', credentials: 'NONE' });
    return result;
  }
  async dispatch(command: ExecutionCommand & { tenant_id: string }) { return this.transition(command, command.status, 'DISPATCH_REJECTED', { code: 'SHADOW_DISPATCH_DISABLED', credentials: 'NONE' }); }
  async transition(command: ExecutionCommand & { tenant_id: string }, from: ExecutionStatus | null, to: ExecutionStatus, payload: Record<string, unknown>) {
    if (from !== null && !transitions[from].includes(to)) throw new Error(`INVALID_EXECUTION_TRANSITION:${from}:${to}`);
    const next = { ...command, status: to };
    const updated = from === null ? true : await this.repositories.updateExecution(next, from);
    if (!updated) throw new Error('EXECUTION_STATE_STALE');
    const transition: ExecutionTransition = { tenant_id: command.tenant_id, command_id: command.command_id, transition_id: `${command.command_id}:${to}:${hash(payload).slice(-12)}`, from_status: from, to_status: to, payload, recorded_at: new Date().toISOString() };
    await this.repositories.putExecutionTransition(transition);
    return next;
  }
}

export class ExecutionAssurance extends ShadowExecutionAssurance {
  constructor(repositories: PlatformRepositories, private readonly credentials: ConnectorCredentialProvider) { super(repositories); }
  async dispatchAuthorized(command: ExecutionCommand & { tenant_id: string }, revalidate: () => Promise<boolean>) {
    if (Date.parse(command.expires_at) <= Date.now() || !(await revalidate())) return this.dispatch(command);
    const credential = await this.credentials.getCredential(command.credential_scope, command.expires_at);
    if (!credential.token || Date.parse(credential.expiresAt) <= Date.now()) return this.transition(command, command.status, 'DISPATCH_FAILED', { code: 'CREDENTIAL_UNAVAILABLE' });
    return this.transition({ ...command, dispatched_at: new Date().toISOString() }, command.status, 'DISPATCHED', { external_idempotency_key: command.external_idempotency_key, credential_scope: command.credential_scope });
  }
}
