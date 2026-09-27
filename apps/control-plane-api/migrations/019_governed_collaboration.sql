BEGIN;

-- Collaboration is an operational record, never a detached chat stream.
CREATE TABLE IF NOT EXISTS collaboration_records (
  tenant_id text NOT NULL,
  collaboration_id text NOT NULL,
  primitive text NOT NULL CHECK (primitive IN ('Discuss','Request','Assign','Handoff','Share','Follow')),
  object_type text NOT NULL,
  object_id text NOT NULL,
  state_version bigint NOT NULL CHECK (state_version >= 0),
  actor_id text NOT NULL,
  visibility_scope text NOT NULL,
  status text NOT NULL,
  payload jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now(),
  expires_at timestamptz,
  PRIMARY KEY (tenant_id, collaboration_id)
);

CREATE INDEX IF NOT EXISTS collaboration_records_object_idx
  ON collaboration_records (tenant_id, object_type, object_id, created_at, collaboration_id);

ALTER TABLE collaboration_records ENABLE ROW LEVEL SECURITY;
ALTER TABLE collaboration_records FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS collaboration_records_tenant_isolation ON collaboration_records;
CREATE POLICY collaboration_records_tenant_isolation ON collaboration_records
  USING (tenant_id = current_setting('app.tenant_id', true))
  WITH CHECK (tenant_id = current_setting('app.tenant_id', true));

REVOKE ALL ON collaboration_records FROM PUBLIC;
GRANT SELECT, INSERT ON collaboration_records TO cerebrum_app;
GRANT SELECT ON collaboration_records TO cerebrum_audit;

INSERT INTO schema_migrations(version)
VALUES ('019_governed_collaboration')
ON CONFLICT DO NOTHING;

COMMIT;
