import { describe, expect, it, vi } from 'vitest';
import { ControlPlaneClient, ControlPlaneError } from './controlPlaneClient';

describe('Control Plane browser boundary', () => {
  it('adds authorization and parses canonical responses', async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify({ data: { version: 142, values: {} }, meta: { correlation_id: 'c1', contract_version: 'v1' } }), { status: 200, headers: { 'content-type': 'application/json' } }));
    vi.stubGlobal('fetch', fetchMock);
    const client = new ControlPlaneClient(() => 'test-token');
    await expect(client.state('memphis-fulfillment')).resolves.toEqual({ version: 142, values: {} });
    expect(fetchMock.mock.calls[0][1]).toMatchObject({ headers: expect.any(Headers) });
    expect((fetchMock.mock.calls[0][1] as RequestInit).headers).toBeInstanceOf(Headers);
    expect(((fetchMock.mock.calls[0][1] as RequestInit).headers as Headers).get('authorization')).toBe('Bearer test-token');
  });

  it('surfaces structured permission failures without exposing transport internals', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(JSON.stringify({ error: { code: 'PERMISSION_DENIED', message: 'Not permitted', correlation_id: 'c2' } }), { status: 403, headers: { 'content-type': 'application/json' } })));
    await expect(new ControlPlaneClient(() => undefined).incident('INC-1042')).rejects.toEqual(expect.objectContaining<Partial<ControlPlaneError>>({ code: 'PERMISSION_DENIED', status: 403 }));
  });
});
