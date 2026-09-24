import { describe, expect, it } from 'vitest';
import { CONTRACT_VERSION, openApiDocument, validateBinding } from '../../packages/contracts/src/index.js';

describe('shared API contracts', () => {
  it('accepts a complete request binding and rejects missing identity fields', () => {
    const binding = { tenant_id: 'meridian-demo', actor_id: 'operator-01', correlation_id: 'corr-1', trace_id: 'trace-1', idempotency_key: 'op-1', contract_version: CONTRACT_VERSION, request_timestamp: new Date().toISOString() };
    expect(validateBinding(binding)).toBe(true);
    expect(validateBinding({ ...binding, actor_id: '' })).toBe(false);
  });

  it('publishes every governed lifecycle route in the OpenAPI document', () => {
    const document = openApiDocument();
    for (const path of ['/v1/events', '/v1/incidents/{id}', '/v1/state/{scopeId}', '/v1/proposals', '/v1/reviews', '/v1/shadow-evaluations', '/v1/outcomes', '/v1/receipts/{id}', '/v1/reconstructions/{incidentId}']) {
      expect(document.paths).toHaveProperty(path);
    }
    expect(document.info.version).toBe(CONTRACT_VERSION);
  });
});
