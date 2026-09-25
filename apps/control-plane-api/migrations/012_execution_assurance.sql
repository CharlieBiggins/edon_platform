BEGIN;
CREATE TABLE IF NOT EXISTS execution_commands (
  tenant_id text NOT NULL, command_id text NOT NULL, incident_id text NOT NULL, proposal_id text NOT NULL,
  status text NOT NULL, command_hash text NOT NULL, authorization_id text NOT NULL, proposal_hash text NOT NULL,
  state_version bigint NOT NULL, external_idempotency_key text NOT NULL, payload jsonb NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(), updated_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (tenant_id, command_id), UNIQUE (tenant_id, external_idempotency_key)
);
CREATE TABLE IF NOT EXISTS execution_transitions (
  tenant_id text NOT NULL, transition_id text NOT NULL, command_id text NOT NULL, from_status text,
  to_status text NOT NULL, payload jsonb NOT NULL, recorded_at timestamptz NOT NULL,
  PRIMARY KEY (tenant_id, transition_id)
);
CREATE OR REPLACE FUNCTION prevent_execution_binding_mutation() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  IF NEW.command_hash <> OLD.command_hash OR NEW.authorization_id <> OLD.authorization_id OR NEW.proposal_hash <> OLD.proposal_hash OR NEW.state_version <> OLD.state_version OR NEW.external_idempotency_key <> OLD.external_idempotency_key OR NEW.tenant_id <> OLD.tenant_id OR NEW.command_id <> OLD.command_id THEN
    RAISE EXCEPTION 'immutable execution binding';
  END IF;
  RETURN NEW;
END $$;
DROP TRIGGER IF EXISTS execution_binding_immutable ON execution_commands;
CREATE TRIGGER execution_binding_immutable BEFORE UPDATE ON execution_commands FOR EACH ROW EXECUTE FUNCTION prevent_execution_binding_mutation();
ALTER TABLE execution_commands ENABLE ROW LEVEL SECURITY; ALTER TABLE execution_commands FORCE ROW LEVEL SECURITY;
ALTER TABLE execution_transitions ENABLE ROW LEVEL SECURITY; ALTER TABLE execution_transitions FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS execution_commands_tenant_isolation ON execution_commands;
CREATE POLICY execution_commands_tenant_isolation ON execution_commands USING (tenant_id=current_setting('app.tenant_id',true)) WITH CHECK (tenant_id=current_setting('app.tenant_id',true));
DROP POLICY IF EXISTS execution_transitions_tenant_isolation ON execution_transitions;
CREATE POLICY execution_transitions_tenant_isolation ON execution_transitions USING (tenant_id=current_setting('app.tenant_id',true)) WITH CHECK (tenant_id=current_setting('app.tenant_id',true));
REVOKE ALL ON execution_commands, execution_transitions FROM PUBLIC;
GRANT SELECT, INSERT, UPDATE ON execution_commands TO cerebrum_app;
GRANT SELECT, INSERT ON execution_transitions TO cerebrum_app;
GRANT SELECT ON execution_commands, execution_transitions TO cerebrum_audit;
REVOKE DELETE ON execution_commands, execution_transitions FROM cerebrum_app, cerebrum_audit;
INSERT INTO schema_migrations(version) VALUES ('012_execution_assurance') ON CONFLICT DO NOTHING;
COMMIT;
