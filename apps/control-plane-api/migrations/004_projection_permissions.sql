BEGIN;

GRANT SELECT, INSERT, UPDATE ON state_snapshots, incidents TO cerebrum_app;
REVOKE DELETE ON state_snapshots, incidents FROM cerebrum_app, cerebrum_audit;
GRANT SELECT ON state_snapshots, incidents TO cerebrum_audit;

ALTER TABLE state_snapshots ENABLE ROW LEVEL SECURITY;
ALTER TABLE state_snapshots FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS state_snapshot_tenant_isolation ON state_snapshots;
CREATE POLICY state_snapshot_tenant_isolation ON state_snapshots
  USING (tenant_id = current_setting('app.tenant_id', true))
  WITH CHECK (tenant_id = current_setting('app.tenant_id', true));

ALTER TABLE idempotency_keys ENABLE ROW LEVEL SECURITY;
ALTER TABLE idempotency_keys FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS idempotency_tenant_isolation ON idempotency_keys;
CREATE POLICY idempotency_tenant_isolation ON idempotency_keys
  USING (tenant_id = current_setting('app.tenant_id', true))
  WITH CHECK (tenant_id = current_setting('app.tenant_id', true));

GRANT SELECT, INSERT ON idempotency_keys TO cerebrum_app;
GRANT SELECT ON idempotency_keys TO cerebrum_audit;
REVOKE UPDATE, DELETE ON idempotency_keys FROM cerebrum_app, cerebrum_audit;

INSERT INTO schema_migrations(version) VALUES ('004_projection_permissions') ON CONFLICT DO NOTHING;
COMMIT;
