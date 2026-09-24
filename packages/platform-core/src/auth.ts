export type Principal = { tenant_id: string; actor_id: string; actor_type: 'HUMAN' | 'AGENT' | 'SYSTEM' | 'CONNECTOR'; roles: string[]; expires_at: string; revoked?: boolean; active?: boolean };
export interface IdentityVerifier { verify(request: unknown): Promise<Principal | null>; }
export class SimulatedIdentityVerifier implements IdentityVerifier { constructor(private principal: Principal) {} async verify() { return this.principal.revoked || new Date(this.principal.expires_at).getTime() <= Date.now() ? null : this.principal; } }

export class OidcIdentityVerifier implements IdentityVerifier {
  private keys = new Map<string, CryptoKey>();
  private loadedAt = 0;
  constructor(private readonly issuer: string, private readonly audience: string, private readonly jwksUrl: string) {}
  private async loadKeys() {
    if (Date.now() - this.loadedAt < 30_000 && this.keys.size) return;
    const response = await fetch(this.jwksUrl); if (!response.ok) throw new Error('JWKS unavailable');
    const body = await response.json() as { keys?: Array<Record<string, string>> };
    this.keys.clear();
    for (const jwk of body.keys ?? []) this.keys.set(jwk.kid, await crypto.subtle.importKey('jwk', jwk as JsonWebKey, { name: 'RSASSA-PKCS1-v1_5', hash: 'SHA-256' }, false, ['verify']));
    this.loadedAt = Date.now();
  }
  async verify(request: { headers?: Record<string, string | string[] | undefined> }): Promise<Principal | null> {
    const header = request.headers?.authorization; const token = Array.isArray(header) ? header[0] : header;
    if (!token?.startsWith('Bearer ')) return null;
    const raw = token.slice(7); const parts = raw.split('.'); if (parts.length !== 3) return null;
    const decodeBytes = (value: string) => Uint8Array.from(atob(value.replace(/-/g, '+').replace(/_/g, '/') + '='.repeat((4 - value.length % 4) % 4)), character => character.charCodeAt(0));
    const decode = (value: string) => JSON.parse(new TextDecoder().decode(decodeBytes(value))) as Record<string, unknown>;
    const head = decode(parts[0]); const claims = decode(parts[1]);
    if (claims.iss !== this.issuer || claims.aud !== this.audience) return null;
    const now = Math.floor(Date.now() / 1000); if (typeof claims.exp !== 'number' || claims.exp <= now || (typeof claims.nbf === 'number' && claims.nbf > now)) return null;
    await this.loadKeys(); const key = this.keys.get(String(head.kid)); if (!key) return null;
    const valid = await crypto.subtle.verify('RSASSA-PKCS1-v1_5', key, decodeBytes(parts[2]), new TextEncoder().encode(`${parts[0]}.${parts[1]}`));
    if (!valid || typeof claims.tenant_id !== 'string' || typeof claims.sub !== 'string' || claims.revoked === true) return null;
    return { tenant_id: claims.tenant_id, actor_id: claims.sub, actor_type: (claims.actor_type as Principal['actor_type']) ?? 'HUMAN', roles: Array.isArray(claims.roles) ? claims.roles.map(String) : [], expires_at: new Date((claims.exp as number) * 1000).toISOString(), active: claims.active !== false };
  }
}


