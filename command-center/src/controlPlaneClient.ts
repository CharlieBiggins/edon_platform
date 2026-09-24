import type { ActionProposal, ApiError, ApiResult, DecisionReceipt, KernelDecision, OutcomeRecord } from '../../packages/contracts/src/index.js';

export type ControlPlaneState = { version: number; values: Record<string, unknown> };
export type Reconstruction = { incident_id: string; events: unknown[]; state: ControlPlaneState };
export class ControlPlaneError extends Error { constructor(public readonly code: string, public readonly status: number, message: string) { super(message); } }
export class ControlPlaneClient {
  private readonly baseUrl = (import.meta.env.VITE_CONTROL_PLANE_API_URL as string | undefined)?.replace(/\/$/, '') ?? '';
  constructor(private readonly tokenProvider: () => string | undefined = () => (globalThis as { __CEREBRUM_TOKEN__?: string }).__CEREBRUM_TOKEN__) {}
  private async request<T>(path: string, init: RequestInit = {}, signal?: AbortSignal): Promise<T> {
    const controller = new AbortController(); const timeout = setTimeout(() => controller.abort(), 10_000); if (signal) signal.addEventListener('abort', () => controller.abort(), { once: true });
    try { const token = this.tokenProvider(); const headers = new Headers(init.headers); headers.set('accept', 'application/json'); if (token) headers.set('authorization', `Bearer ${token}`); const response = await fetch(`${this.baseUrl}${path}`, { ...init, headers, signal: controller.signal }); const body = await response.json() as ApiResult<T> & ApiError; if (!response.ok) throw new ControlPlaneError(body.error?.code ?? 'API_ERROR', response.status, body.error?.message ?? 'Control Plane request failed'); return body.data; } finally { clearTimeout(timeout); }
  }
  state(scopeId: string, signal?: AbortSignal) { return this.request<ControlPlaneState>(`/v1/state/${encodeURIComponent(scopeId)}`, {}, signal); }
  incident(id: string, signal?: AbortSignal) { return this.request<Record<string, unknown>>(`/v1/incidents/${encodeURIComponent(id)}`, {}, signal); }
  proposal(id: string, signal?: AbortSignal) { return this.request<ActionProposal>(`/v1/proposals/${encodeURIComponent(id)}`, {}, signal); }
  decision(proposalId: string, signal?: AbortSignal) { return this.request<KernelDecision>(`/v1/decisions/${encodeURIComponent(proposalId)}`, {}, signal); }
  outcome(id: string, signal?: AbortSignal) { return this.request<OutcomeRecord>(`/v1/outcomes/${encodeURIComponent(id)}`, {}, signal); }
  receipt(id: string, signal?: AbortSignal) { return this.request<DecisionReceipt>(`/v1/receipts/${encodeURIComponent(id)}`, {}, signal); }
  reconstruction(id: string, signal?: AbortSignal) { return this.request<Reconstruction>(`/v1/reconstructions/${encodeURIComponent(id)}`, {}, signal); }
}
export const controlPlaneClient = new ControlPlaneClient();
