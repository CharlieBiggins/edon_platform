BEGIN;
CREATE TABLE IF NOT EXISTS institution_ir_candidates (
  tenant_id text NOT NULL,
  institution_id text NOT NULL,
  candidate_id text NOT NULL,
  version text NOT NULL,
  ir_hash text NOT NULL,
  compiler_version text NOT NULL,
  input_source_hashes jsonb NOT NULL,
  validation_findings jsonb NOT NULL DEFAULT '[]'::jsonb,
  previous_candidate_id text,
  control_graph_diff jsonb NOT NULL DEFAULT '{}'::jsonb,
  status text NOT NULL,
  payload jsonb NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (tenant_id, institution_id, candidate_id)
);
CREATE TABLE IF NOT EXISTS institution_releases (
  tenant_id text NOT NULL,
  institution_id text NOT NULL,
  release_id text NOT NULL,
  candidate_id text NOT NULL,
  version text NOT NULL,
  status text NOT NULL,
  manifest_hash text NOT NULL,
  signature_status text NOT NULL DEFAULT 'SIGNATURE_PENDING',
  signed_by text,
  signed_at timestamptz,
  previous_release_id text,
  rollback_target text,
  payload jsonb NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (tenant_id, institution_id, release_id)
);
DO $$ DECLARE t text; BEGIN
  FOREACH t IN ARRAY ARRAY['institution_ir_candidates','institution_releases'] LOOP
    EXECUTE format('ALTER TABLE %I ENABLE ROW LEVEL SECURITY', t);
    EXECUTE format('ALTER TABLE %I FORCE ROW LEVEL SECURITY', t);
    EXECUTE format('CREATE POLICY %I_tenant_isolation ON %I USING (tenant_id = current_setting(''app.tenant_id'', true)) WITH CHECK (tenant_id = current_setting(''app.tenant_id'', true))', t, t);
    EXECUTE format('GRANT SELECT, INSERT ON %I TO cerebrum_app', t);
    EXECUTE format('GRANT SELECT ON %I TO cerebrum_audit', t);
    EXECUTE format('REVOKE UPDATE, DELETE ON %I FROM cerebrum_app, cerebrum_audit', t);
  END LOOP;
END $$;
INSERT INTO schema_migrations(version) VALUES ('014_institution_releases') ON CONFLICT DO NOTHING;
COMMIT;
