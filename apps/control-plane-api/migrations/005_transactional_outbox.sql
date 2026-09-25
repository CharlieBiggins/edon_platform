BEGIN;

CREATE TABLE IF NOT EXISTS transactional_outbox (
  tenant_id text NOT NULL,
  outbox_id text NOT NULL,
  dedupe_key text NOT NULL,
  topic text NOT NULL,
  aggregate_id text NOT NULL,
  payload jsonb NOT NULL,
  correlation_id text NOT NULL,
  trace_id text NOT NULL,
  state_version bigint,
  status text NOT NULL DEFAULT 'PENDING' CHECK (status IN ('PENDING','PROCESSING','COMPLETED','DEAD_LETTER')),
  attempts integer NOT NULL DEFAULT 0,
  available_at timestamptz NOT NULL DEFAULT now(),
  locked_at timestamptz,
  completed_at timestamptz,
  last_error text,
  created_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (tenant_id, outbox_id),
  UNIQUE (tenant_id, dedupe_key)
);

ALTER TABLE transactional_outbox ENABLE ROW LEVEL SECURITY;
ALTER TABLE transactional_outbox FORCE ROW LEVEL SECURITY;
CREATE POLICY transactional_outbox_tenant_isolation ON transactional_outbox
  USING (tenant_id = current_setting('app.tenant_id', true))
  WITH CHECK (tenant_id = current_setting('app.tenant_id', true));

GRANT SELECT, INSERT, UPDATE ON transactional_outbox TO cerebrum_app;
GRANT SELECT ON transactional_outbox TO cerebrum_audit;
REVOKE DELETE ON transactional_outbox FROM cerebrum_app, cerebrum_audit;

CREATE INDEX IF NOT EXISTS transactional_outbox_ready_idx
  ON transactional_outbox (tenant_id, status, available_at, created_at);

INSERT INTO schema_migrations(version)
VALUES ('005_transactional_outbox')
ON CONFLICT DO NOTHING;
COMMIT;
