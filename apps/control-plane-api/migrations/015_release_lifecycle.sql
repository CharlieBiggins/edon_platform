BEGIN;
ALTER TABLE institution_releases
  ADD COLUMN IF NOT EXISTS lifecycle_state text NOT NULL DEFAULT 'DRAFT',
  ADD COLUMN IF NOT EXISTS version bigint NOT NULL DEFAULT 1,
  ADD COLUMN IF NOT EXISTS correlation_id text,
  ADD COLUMN IF NOT EXISTS trace_id text;
ALTER TABLE institution_releases DROP CONSTRAINT IF EXISTS institution_releases_state_check;
ALTER TABLE institution_releases ADD CONSTRAINT institution_releases_state_check CHECK (lifecycle_state IN ('DRAFT','EXTRACTED','MAPPED','VALIDATED','QUALIFIED','APPROVED','SIGNED','SHADOW','ACTIVE','REJECTED','SUPERSEDED','ROLLED_BACK'));
INSERT INTO schema_migrations(version) VALUES ('015_release_lifecycle') ON CONFLICT DO NOTHING;
COMMIT;
