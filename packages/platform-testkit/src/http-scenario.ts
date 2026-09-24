import { CONTRACT_VERSION, type ApiResult } from '../../contracts/src';

export async function runHttpScenario(baseUrl: string, fetcher: typeof fetch = fetch) {
  const binding = { tenant_id: 'meridian-demo', actor_id: 'operator-01', correlation_id: 'corr-http-1042', trace_id: 'trace-http-1042', idempotency_key: 'idem-http-1042', contract_version: CONTRACT_VERSION, request_timestamp: '2026-09-24T15:24:03.122Z', expected_state_version: 141, evidence_references: ['EV-2081'] };
  const eventBody = { binding, incident_id: 'INC-1042', scope_id: 'memphis-fulfillment', payload: { capacity_units: 260 } };
  const first = await fetcher(`${baseUrl}/v1/events`, { method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify(eventBody) });
  const duplicate = await fetcher(`${baseUrl}/v1/events`, { method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify(eventBody) });
  const state = await fetcher(`${baseUrl}/v1/state/memphis-fulfillment`);
  return { first: await first.json() as ApiResult<unknown>, duplicate: await duplicate.json() as ApiResult<unknown>, state: await state.json() as ApiResult<unknown>, duplicateStatus: duplicate.status };
}
