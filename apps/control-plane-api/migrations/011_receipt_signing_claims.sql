BEGIN;
CREATE TABLE IF NOT EXISTS receipt_signing_claims (
  tenant_id text NOT NULL,
  receipt_id text NOT NULL,
  worker_id text NOT NULL,
  status text NOT NULL DEFAULT 'CLAIMED',
  lease_expires_at timestamptz NOT NULL,
  recorded_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (tenant_id, receipt_id),
  FOREIGN KEY (tenant_id, receipt_id) REFERENCES receipts(tenant_id, receipt_id)
);
ALTER TABLE receipt_signing_claims ENABLE ROW LEVEL SECURITY;
ALTER TABLE receipt_signing_claims FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS receipt_signing_claim_tenant_isolation ON receipt_signing_claims;
CREATE POLICY receipt_signing_claim_tenant_isolation ON receipt_signing_claims USING (tenant_id = current_setting('app.tenant_id', true)) WITH CHECK (tenant_id = current_setting('app.tenant_id', true));
REVOKE ALL ON receipt_signing_claims FROM PUBLIC;
GRANT SELECT, INSERT, UPDATE, REFERENCES ON receipt_signing_claims TO cerebrum_app;
GRANT SELECT ON receipt_signing_claims TO cerebrum_audit;
REVOKE DELETE ON receipt_signing_claims FROM cerebrum_app, cerebrum_audit;
GRANT REFERENCES ON receipts TO cerebrum_app;
INSERT INTO schema_migrations(version) VALUES ('011_receipt_signing_claims') ON CONFLICT DO NOTHING;
COMMIT;
