import type { EventEnvelope } from './contracts';

const fingerprint = (event: EventEnvelope<unknown>) => JSON.stringify(event);

/** In-memory stand-in for the append-only journal used by the reference slice. */
export class AppendOnlyJournal {
  private records: EventEnvelope<unknown>[] = [];
  private fingerprints = new Map<string, string>();

  append<T>(event: EventEnvelope<T>): boolean {
    if (this.records.some(record => record.event_id === event.event_id)) return false;
    this.records.push(event as EventEnvelope<unknown>);
    this.fingerprints.set(event.event_id, fingerprint(event as EventEnvelope<unknown>));
    return true;
  }

  all() { return [...this.records]; }
  replay() {
    return [...this.records]
      .sort((a, b) => a.occurred_at.localeCompare(b.occurred_at))
      .reduce((state, event) => event.event_type === 'STATE_PROJECTED' ? event.state_version_after : state, 141);
  }
  verifyIntegrity() {
    return this.records.every(record => this.fingerprints.get(record.event_id) === fingerprint(record));
  }
}
