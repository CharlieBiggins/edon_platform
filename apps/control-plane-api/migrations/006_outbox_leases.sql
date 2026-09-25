BEGIN;
ALTER TABLE transactional_outbox
  ADD COLUMN IF NOT EXISTS lease_expires_at timestamptz,
  ADD COLUMN IF NOT EXISTS worker_id text,
  ADD COLUMN IF NOT EXISTS last_error_code text,
  ADD COLUMN IF NOT EXISTS last_error_metadata jsonb;
CREATE INDEX IF NOT EXISTS transactional_outbox_lease_idx
  ON transactional_outbox (tenant_id, status, lease_expires_at);
INSERT INTO schema_migrations(version)
VALUES ('006_outbox_leases') ON CONFLICT DO NOTHING;
COMMIT;
