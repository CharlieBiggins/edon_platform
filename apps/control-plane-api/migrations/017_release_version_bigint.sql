BEGIN;

-- Migration 014 created a text version column before the lifecycle migration
-- introduced the authoritative numeric version. Normalize legacy rows and make
-- the optimistic-concurrency column a real bigint so version arithmetic and
-- CAS predicates are performed by PostgreSQL.
ALTER TABLE institution_releases
  ALTER COLUMN version TYPE bigint
  USING version::bigint;

INSERT INTO schema_migrations(version)
VALUES ('017_release_version_bigint')
ON CONFLICT DO NOTHING;

COMMIT;
