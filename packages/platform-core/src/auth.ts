export type Principal = { tenant_id: string; actor_id: string; actor_type: 'HUMAN' | 'AGENT' | 'SYSTEM' | 'CONNECTOR'; roles: string[]; expires_at: string; revoked?: boolean };
export interface IdentityVerifier { verify(request: unknown): Promise<Principal | null>; }
export class SimulatedIdentityVerifier implements IdentityVerifier { constructor(private principal: Principal) {} async verify() { return this.principal.revoked || new Date(this.principal.expires_at).getTime() <= Date.now() ? null : this.principal; } }


