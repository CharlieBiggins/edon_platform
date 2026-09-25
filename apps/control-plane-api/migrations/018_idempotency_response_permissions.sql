BEGIN;

-- Idempotency reservations are created before work and finalized with the
-- committed response in the same transaction. Permit only that response
-- column to be updated; keys and tenant ownership remain immutable.
GRANT UPDATE (response) ON idempotency_keys TO cerebrum_app;
REVOKE UPDATE (tenant_id, key, created_at) ON idempotency_keys FROM cerebrum_app, cerebrum_audit;

INSERT INTO schema_migrations(version)
VALUES ('018_idempotency_response_permissions')
ON CONFLICT DO NOTHING;

COMMIT;
