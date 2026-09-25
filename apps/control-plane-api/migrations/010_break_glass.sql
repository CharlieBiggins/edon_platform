BEGIN;
CREATE TABLE IF NOT EXISTS break_glass_grants (
  tenant_id text NOT NULL,
  grant_id text NOT NULL,
  incident_id text NOT NULL,
  payload jsonb NOT NULL,
  status text NOT NULL,
  expires_at timestamptz,
  recorded_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (tenant_id, grant_id)
);
ALTER TABLE break_glass_grants ENABLE ROW LEVEL SECURITY;
ALTER TABLE break_glass_grants FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS break_glass_tenant_isolation ON break_glass_grants;
CREATE POLICY break_glass_tenant_isolation ON break_glass_grants USING (tenant_id = current_setting('app.tenant_id', true)) WITH CHECK (tenant_id = current_setting('app.tenant_id', true));
REVOKE ALL ON break_glass_grants FROM PUBLIC;
GRANT SELECT, INSERT, UPDATE ON break_glass_grants TO cerebrum_app;
GRANT SELECT ON break_glass_grants TO cerebrum_audit;
REVOKE DELETE ON break_glass_grants FROM cerebrum_app, cerebrum_audit;
INSERT INTO schema_migrations(version) VALUES ('010_break_glass') ON CONFLICT DO NOTHING;
COMMIT;
