BEGIN;

CREATE TABLE IF NOT EXISTS evidence_records (tenant_id text NOT NULL, evidence_id text NOT NULL, payload jsonb NOT NULL, recorded_at timestamptz NOT NULL DEFAULT now(), PRIMARY KEY (tenant_id, evidence_id));
CREATE TABLE IF NOT EXISTS incidents (tenant_id text NOT NULL, incident_id text NOT NULL, scope_id text NOT NULL, state_version bigint NOT NULL DEFAULT 0, status text NOT NULL DEFAULT 'OPEN', payload jsonb NOT NULL DEFAULT '{}'::jsonb, recorded_at timestamptz NOT NULL DEFAULT now(), PRIMARY KEY (tenant_id, incident_id));
CREATE TABLE IF NOT EXISTS proposals (tenant_id text NOT NULL, proposal_id text NOT NULL, payload jsonb NOT NULL, recorded_at timestamptz NOT NULL DEFAULT now(), PRIMARY KEY (tenant_id, proposal_id));
CREATE TABLE IF NOT EXISTS human_reviews (tenant_id text NOT NULL, review_id text NOT NULL, payload jsonb NOT NULL, recorded_at timestamptz NOT NULL DEFAULT now(), PRIMARY KEY (tenant_id, review_id));
CREATE TABLE IF NOT EXISTS kernel_decisions (tenant_id text NOT NULL, decision_id text NOT NULL, proposal_id text NOT NULL, payload jsonb NOT NULL, recorded_at timestamptz NOT NULL DEFAULT now(), PRIMARY KEY (tenant_id, decision_id));
CREATE TABLE IF NOT EXISTS mandates (tenant_id text NOT NULL, mandate_id text NOT NULL, payload jsonb NOT NULL, recorded_at timestamptz NOT NULL DEFAULT now(), PRIMARY KEY (tenant_id, mandate_id));
CREATE TABLE IF NOT EXISTS shadow_evaluations (tenant_id text NOT NULL, proposal_id text NOT NULL, payload jsonb NOT NULL, recorded_at timestamptz NOT NULL DEFAULT now(), PRIMARY KEY (tenant_id, proposal_id));
CREATE TABLE IF NOT EXISTS outcomes (tenant_id text NOT NULL, outcome_id text NOT NULL, payload jsonb NOT NULL, recorded_at timestamptz NOT NULL DEFAULT now(), PRIMARY KEY (tenant_id, outcome_id));

DO $$ DECLARE t text; BEGIN
  FOREACH t IN ARRAY ARRAY['evidence_records','incidents','proposals','human_reviews','kernel_decisions','mandates','shadow_evaluations','outcomes'] LOOP
    EXECUTE format('ALTER TABLE %I ENABLE ROW LEVEL SECURITY', t);
    EXECUTE format('ALTER TABLE %I FORCE ROW LEVEL SECURITY', t);
    EXECUTE format('DROP POLICY IF EXISTS tenant_isolation ON %I', t);
    EXECUTE format('CREATE POLICY tenant_isolation ON %I USING (tenant_id = current_setting(''app.tenant_id'', true)) WITH CHECK (tenant_id = current_setting(''app.tenant_id'', true))', t);
    EXECUTE format('REVOKE UPDATE, DELETE ON %I FROM PUBLIC, cerebrum_app, cerebrum_audit', t);
    EXECUTE format('GRANT SELECT, INSERT ON %I TO cerebrum_app', t);
    EXECUTE format('GRANT SELECT ON %I TO cerebrum_audit', t);
  END LOOP;
END $$;

INSERT INTO schema_migrations(version) VALUES ('003_lifecycle_records') ON CONFLICT DO NOTHING;
COMMIT;
