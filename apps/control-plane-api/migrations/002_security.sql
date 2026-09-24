BEGIN;
DO $$ BEGIN
  CREATE ROLE cerebrum_migrator NOLOGIN;
EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN
  CREATE ROLE cerebrum_app NOLOGIN;
EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN
  CREATE ROLE cerebrum_audit NOLOGIN;
EXCEPTION WHEN duplicate_object THEN NULL; END $$;
ALTER TABLE journal_events FORCE ROW LEVEL SECURITY;
ALTER TABLE receipts FORCE ROW LEVEL SECURITY;
REVOKE ALL ON journal_events, receipts FROM PUBLIC;
GRANT SELECT, INSERT ON journal_events TO cerebrum_app;
GRANT SELECT, INSERT ON receipts TO cerebrum_app;
GRANT SELECT ON journal_events, receipts TO cerebrum_audit;
REVOKE UPDATE, DELETE ON journal_events, receipts FROM cerebrum_app, cerebrum_audit;
INSERT INTO schema_migrations(version) VALUES ('002_security') ON CONFLICT DO NOTHING;
COMMIT;
