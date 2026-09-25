import type { OutboxMessage, PlatformRepositories } from './repositories.js';

export type OutboxHandler = (message: OutboxMessage) => Promise<void>;
export type OutboxMessageVerifier = (message: OutboxMessage) => Promise<void>;

/** Processes one durable message. External work runs after the claim and outside a DB transaction. */
export class DurableOutboxWorker {
  constructor(
    private readonly repositories: PlatformRepositories,
    private readonly tenantId: string,
    private readonly workerId: string,
    private readonly handle: OutboxHandler,
    private readonly verify: OutboxMessageVerifier,
    private readonly maxAttempts = 5,
    private readonly leaseMs = 30000,
  ) {}

  async processOnce(): Promise<'IDLE' | 'COMPLETED' | 'RETRYING' | 'DEAD_LETTER'> {
    const message = await this.repositories.transaction(this.tenantId, repositories => repositories.claimOutbox(this.tenantId, this.workerId, this.leaseMs));
    if (!message) return 'IDLE';
    try {
      await this.verify(message);
      await this.handle(message);
      await this.repositories.transaction(this.tenantId, repositories => repositories.completeOutbox(this.tenantId, message.outbox_id));
      return 'COMPLETED';
    } catch (error) {
      const attempts = message.attempts ?? 1;
      const base = Math.min(30000, 250 * 2 ** Math.max(0, attempts - 1));
      const jittered = Math.round(base * (0.8 + Math.random() * 0.4));
      return this.repositories.transaction(this.tenantId, repositories => repositories.retryOutbox(this.tenantId, message.outbox_id, error instanceof Error ? error.message : 'worker failure', this.maxAttempts, jittered));
    }
  }
}
