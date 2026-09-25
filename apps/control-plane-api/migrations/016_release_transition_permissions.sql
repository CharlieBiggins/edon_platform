BEGIN;

-- Only lifecycle metadata is mutable through the governed transition service.
-- Manifest-bound release fields remain immutable to the application role.
GRANT UPDATE (lifecycle_state, version, correlation_id, trace_id)
ON institution_releases TO cerebrum_app;
REVOKE UPDATE (manifest_hash, payload, candidate_id, institution_id, release_id, tenant_id)
ON institution_releases FROM cerebrum_app, cerebrum_audit;
REVOKE DELETE ON institution_releases FROM cerebrum_app, cerebrum_audit;

INSERT INTO schema_migrations(version)
VALUES ('016_release_transition_permissions')
ON CONFLICT DO NOTHING;
COMMIT;
