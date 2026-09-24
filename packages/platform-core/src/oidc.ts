declare const Buffer: { from(value: string, encoding: string): { toString(encoding: string): string } };
export type OidcClaims = { sub: string; iss: string; aud: string | string[]; exp: number; nbf?: number; tenant_id: string; roles?: string[]; actor_status?: 'ACTIVE' | 'DISABLED' };
export type JwtVerifier = (header: Record<string, unknown>, signingInput: string, signature: string) => Promise<boolean>;
export class OidcJwksVerifier {
  constructor(private readonly issuer: string, private readonly audience: string, private readonly verifySignature: JwtVerifier, private readonly now = () => Math.floor(Date.now() / 1000)) {}
  async verifyToken(token: string, expectedTenant?: string, requiredRole?: string): Promise<OidcClaims | null> {
    const parts = token.split('.'); if (parts.length !== 3) return null;
    try { const decode = (value: string) => JSON.parse(Buffer.from(value, 'base64url').toString('utf8')) as Record<string, unknown>; const header = decode(parts[0]); const claims = decode(parts[1]) as unknown as OidcClaims; if (!(await this.verifySignature(header, `${parts[0]}.${parts[1]}`, parts[2]))) return null; if (claims.iss !== this.issuer || !(Array.isArray(claims.aud) ? claims.aud.includes(this.audience) : claims.aud === this.audience) || claims.exp <= this.now() || (claims.nbf !== undefined && claims.nbf > this.now()) || claims.actor_status === 'DISABLED' || (expectedTenant && claims.tenant_id !== expectedTenant) || (requiredRole && !claims.roles?.includes(requiredRole))) return null; return claims; } catch { return null; }
  }
}


