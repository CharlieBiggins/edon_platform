import type { StateProjector } from './contracts.js';
export class ReplayableStateProjector implements StateProjector {
  project(events: { event_type: string; state_version_after: number; payload: unknown; occurred_at?: string }[]) {
    const projections = events.filter(event => {
      if (event.event_type !== 'STATE_PROJECTED' || event.state_version_after <= 141) return false;
      const payload = event.payload as { capacity_units?: unknown; commitments_at_risk?: unknown };
      return typeof payload.capacity_units === 'number' && payload.capacity_units >= 0 && payload.capacity_units <= 10000
        && typeof payload.commitments_at_risk === 'number' && payload.commitments_at_risk >= 0;
    })
      .sort((a, b) => (a.occurred_at ?? '').localeCompare(b.occurred_at ?? ''));
    const projection = projections.at(-1);
    const payload = projection?.payload as { capacity_units?: number; commitments_at_risk?: number } | undefined;
    return { version: projection?.state_version_after ?? 141, values: {
      memphis_capacity: payload?.capacity_units ?? 480,
      carrier_commitment: projection ? 'at_risk' : 'normal',
      commitments_at_risk: payload?.commitments_at_risk ?? 0,
    } };
  }
}


