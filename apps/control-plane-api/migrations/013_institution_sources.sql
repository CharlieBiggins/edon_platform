BEGIN;

CREATE TABLE IF NOT EXISTS institution_sources (
  tenant_id text NOT NULL,
  institution_id text NOT NULL,
  source_id text NOT NULL,
  source_version text NOT NULL,
  owner_id text NOT NULL,
  provenance text NOT NULL,
  sensitivity text NOT NULL,
  effective_from timestamptz NOT NULL,
  effective_to timestamptz,
  content_hash text NOT NULL,
  classification_status text NOT NULL DEFAULT 'PENDING',
  ingestion_timestamp timestamptz NOT NULL DEFAULT now(),
  payload jsonb NOT NULL DEFAULT '{}'::jsonb,
  PRIMARY KEY (tenant_id, institution_id, source_id, source_version)
);
ALTER TABLE institution_sources ENABLE ROW LEVEL SECURITY;
ALTER TABLE institution_sources FORCE ROW LEVEL SECURITY;
CREATE POLICY institution_sources_tenant_isolation ON institution_sources
  USING (tenant_id = current_setting('app.tenant_id', true))
  WITH CHECK (tenant_id = current_setting('app.tenant_id', true));
GRANT SELECT, INSERT ON institution_sources TO cerebrum_app;
GRANT SELECT ON institution_sources TO cerebrum_audit;
REVOKE UPDATE, DELETE ON institution_sources FROM cerebrum_app, cerebrum_audit;

INSERT INTO schema_migrations(version) VALUES ('013_institution_sources') ON CONFLICT DO NOTHING;
COMMIT;
