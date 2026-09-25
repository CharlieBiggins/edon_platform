BEGIN;

CREATE TABLE IF NOT EXISTS receipt_custody (
  tenant_id text NOT NULL,
  receipt_id text NOT NULL,
  payload jsonb NOT NULL,
  recorded_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (tenant_id, receipt_id),
  FOREIGN KEY (tenant_id, receipt_id) REFERENCES receipts(tenant_id, receipt_id)
);
ALTER TABLE receipt_custody ENABLE ROW LEVEL SECURITY;
ALTER TABLE receipt_custody FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS receipt_custody_tenant_isolation ON receipt_custody;
CREATE POLICY receipt_custody_tenant_isolation ON receipt_custody
  USING (tenant_id = current_setting('app.tenant_id', true))
  WITH CHECK (tenant_id = current_setting('app.tenant_id', true));
REVOKE ALL ON receipt_custody FROM PUBLIC;
GRANT SELECT, INSERT ON receipt_custody TO cerebrum_app;
GRANT REFERENCES ON receipts TO cerebrum_app;
GRANT SELECT ON receipt_custody TO cerebrum_audit;
REVOKE UPDATE, DELETE ON receipt_custody FROM cerebrum_app, cerebrum_audit;
INSERT INTO schema_migrations(version) VALUES ('009_receipt_custody') ON CONFLICT DO NOTHING;
COMMIT;
