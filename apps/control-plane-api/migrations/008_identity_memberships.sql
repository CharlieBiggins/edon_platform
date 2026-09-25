BEGIN;
CREATE TABLE IF NOT EXISTS actor_memberships (
  tenant_id text NOT NULL,
  actor_id text NOT NULL,
  role text NOT NULL,
  active boolean NOT NULL DEFAULT true,
  facility_scope text,
  mandate_expires_at timestamptz,
  financial_limit numeric,
  PRIMARY KEY (tenant_id, actor_id, role)
);
ALTER TABLE actor_memberships ENABLE ROW LEVEL SECURITY;
ALTER TABLE actor_memberships FORCE ROW LEVEL SECURITY;
CREATE POLICY actor_membership_tenant_isolation ON actor_memberships
  USING (tenant_id = current_setting('app.tenant_id', true))
  WITH CHECK (tenant_id = current_setting('app.tenant_id', true));
GRANT SELECT ON actor_memberships TO cerebrum_app, cerebrum_audit;
REVOKE INSERT, UPDATE, DELETE ON actor_memberships FROM cerebrum_app, cerebrum_audit;
INSERT INTO actor_memberships (tenant_id,actor_id,role,active,facility_scope,mandate_expires_at,financial_limit)
VALUES ('meridian-demo','operator-01','operator',true,'*','2099-01-01T00:00:00Z',10000),
       ('meridian-demo','audit-01','auditor',true,'*','2099-01-01T00:00:00Z',0)
ON CONFLICT DO NOTHING;
INSERT INTO schema_migrations(version) VALUES ('008_identity_memberships') ON CONFLICT DO NOTHING;
COMMIT;
