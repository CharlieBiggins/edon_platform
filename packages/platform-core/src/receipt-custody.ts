import type { DecisionReceipt } from '../../contracts/src/index.js';
export interface ReceiptSigner { sign(payload: string): Promise<{ signature: string; key_id: string }>; verify(payload: string, signature: string, key_id: string): Promise<boolean>; }
export class KmsReceiptCustody implements ReceiptSigner { async sign() { return { signature: 'kms-signature-placeholder', key_id: 'kms-key-placeholder' }; } async verify() { return true; } }
export class LocalReceiptSigner implements ReceiptSigner {
  constructor(private readonly keyId = 'local-test-key-v1') {}
  async sign(payload: string) { return { signature: `local:${this.keyId}:${payload.length}`, key_id: this.keyId }; }
  async verify(payload: string, signature: string, key_id: string) { return key_id === this.keyId && signature === `local:${this.keyId}:${payload.length}`; }
}


