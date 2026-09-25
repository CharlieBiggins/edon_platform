import { createHash } from 'node:crypto';
import { mkdir, writeFile } from 'node:fs/promises';
import { resolve } from 'node:path';
const dbUrl = process.env.CEREBRUM_DIGEST_DB_URL ?? process.env.MIGRATOR_DATABASE_URL;
const tenant = process.env.CEREBRUM_RELEASE_TENANT ?? 'meridian-demo';
const releaseId = process.env.CEREBRUM_CANONICAL_RELEASE_ID ?? 'REL-CANONICAL-SIGNED';
const artifactDir = resolve(process.env.CEREBRUM_ARTIFACT_DIR ?? 'artifacts');
await mkdir(artifactDir, { recursive: true });
const { Pool } = await import('pg');
const pool = new Pool({ connectionString: dbUrl });
const q = (sql, values = []) => pool.query(sql, values);
const rows = async (sql, values = []) => (await q(sql, values)).rows;
const snapshot = {
  release: await rows('SELECT tenant_id,institution_id,release_id,candidate_id,version,status,lifecycle_state,manifest_hash,signature_status,signed_by,signed_at,previous_release_id,rollback_target,payload FROM institution_releases WHERE tenant_id=$1 AND release_id=$2', [tenant, releaseId]),
  candidate: await rows('SELECT tenant_id,institution_id,candidate_id,version,ir_hash,compiler_version,input_source_hashes,validation_findings,previous_candidate_id,control_graph_diff,status,payload FROM institution_ir_candidates WHERE tenant_id=$1 AND candidate_id=(SELECT candidate_id FROM institution_releases WHERE tenant_id=$1 AND release_id=$2)', [tenant, releaseId]),
  events: await rows('SELECT event_id,event_type,actor_id,actor_type,occurred_at,recorded_at,state_version_before,state_version_after,payload_hash,previous_record_hash,payload FROM journal_events WHERE tenant_id=$1 AND incident_id=$2 ORDER BY recorded_at,event_id', [tenant, releaseId]),
  outbox: await rows('SELECT outbox_id,dedupe_key,topic,aggregate_id,payload,correlation_id,trace_id,state_version FROM transactional_outbox WHERE tenant_id=$1 AND aggregate_id=$2 ORDER BY outbox_id', [tenant, releaseId]),
  idempotency: await rows('SELECT key,response FROM idempotency_keys WHERE tenant_id=$1 AND key LIKE $2 ORDER BY key', [tenant, `institution-release-transition:${releaseId}:%`]),
};
const canonical = JSON.stringify(snapshot);
const digest = createHash('sha256').update(canonical).digest('hex');
const output = { release_id: releaseId, tenant_id: tenant, digest: `sha256:${digest}`, row_counts: Object.fromEntries(Object.entries(snapshot).map(([key, value]) => [key, value.length])), snapshot };
await writeFile(resolve(artifactDir, process.env.CEREBRUM_DIGEST_OUTPUT ?? 'release-digest.json'), JSON.stringify(output, null, 2));
await pool.end();
