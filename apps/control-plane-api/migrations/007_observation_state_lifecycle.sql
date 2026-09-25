BEGIN;
ALTER TABLE state_snapshots ADD COLUMN IF NOT EXISTS state_hash text;
CREATE TABLE IF NOT EXISTS state_diffs (
  tenant_id text NOT NULL,
  scope_id text NOT NULL,
  version bigint NOT NULL,
  diff jsonb NOT NULL,
  state_hash text NOT NULL,
  recorded_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (tenant_id, scope_id, version)
);
CREATE TABLE IF NOT EXISTS evidence_relationships (
  tenant_id text NOT NULL,
  relationship_id text NOT NULL,
  event_id text NOT NULL,
  evidence_id text NOT NULL,
  relationship_type text NOT NULL CHECK (relationship_type IN ('ADMITTED_FOR','RESTRICTED_FROM','DISPUTED_BY','REJECTED_FOR')),
  recorded_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (tenant_id, relationship_id)
);
DO $$ DECLARE t text; BEGIN
  FOREACH t IN ARRAY ARRAY['state_diffs','evidence_relationships'] LOOP
    EXECUTE format('ALTER TABLE %I ENABLE ROW LEVEL SECURITY', t);
    EXECUTE format('ALTER TABLE %I FORCE ROW LEVEL SECURITY', t);
    EXECUTE format('CREATE POLICY %I_tenant_isolation ON %I USING (tenant_id = current_setting(''app.tenant_id'', true)) WITH CHECK (tenant_id = current_setting(''app.tenant_id'', true))', t, t);
    EXECUTE format('GRANT SELECT, INSERT ON %I TO cerebrum_app', t);
    EXECUTE format('GRANT SELECT ON %I TO cerebrum_audit', t);
    EXECUTE format('REVOKE UPDATE, DELETE ON %I FROM cerebrum_app, cerebrum_audit', t);
  END LOOP;
END $$;
GRANT SELECT, INSERT, UPDATE ON state_snapshots TO cerebrum_app;
GRANT SELECT ON state_snapshots TO cerebrum_audit;
INSERT INTO schema_migrations(version) VALUES ('007_observation_state_lifecycle') ON CONFLICT DO NOTHING;
COMMIT;
