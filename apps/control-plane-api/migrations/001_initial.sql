-- Apply with a migration runner in order; do not use schema.sql as the production migration mechanism.
BEGIN;
CREATE TABLE IF NOT EXISTS schema_migrations (version text PRIMARY KEY, applied_at timestamptz NOT NULL DEFAULT now());
CREATE TABLE IF NOT EXISTS journal_events (tenant_id text NOT NULL, event_id text NOT NULL, event_type text NOT NULL, payload jsonb NOT NULL, recorded_at timestamptz NOT NULL, PRIMARY KEY (tenant_id,event_id));
CREATE TABLE IF NOT EXISTS idempotency_keys (tenant_id text NOT NULL, key text NOT NULL, response jsonb NOT NULL, PRIMARY KEY (tenant_id,key));
CREATE TABLE IF NOT EXISTS state_snapshots (tenant_id text NOT NULL, scope_id text NOT NULL, version bigint NOT NULL, values jsonb NOT NULL, PRIMARY KEY (tenant_id,scope_id));
INSERT INTO schema_migrations(version) VALUES ('001_initial') ON CONFLICT DO NOTHING;
CREATE TABLE IF NOT EXISTS receipts (tenant_id text NOT NULL, receipt_id text NOT NULL, payload jsonb NOT NULL, PRIMARY KEY (tenant_id,receipt_id));
ALTER TABLE journal_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE receipts ENABLE ROW LEVEL SECURITY;
CREATE POLICY journal_tenant_isolation ON journal_events USING (tenant_id = current_setting('app.tenant_id', true)) WITH CHECK (tenant_id = current_setting('app.tenant_id', true));
CREATE POLICY receipt_tenant_isolation ON receipts USING (tenant_id = current_setting('app.tenant_id', true)) WITH CHECK (tenant_id = current_setting('app.tenant_id', true));
REVOKE UPDATE, DELETE ON journal_events FROM PUBLIC;
REVOKE UPDATE, DELETE ON receipts FROM PUBLIC;
COMMIT;
