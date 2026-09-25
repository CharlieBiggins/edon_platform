import { mkdir, writeFile } from 'node:fs/promises';
import { resolve } from 'node:path';
const adminUrl = process.env.MIGRATOR_DATABASE_URL;
const appUrl = process.env.DATABASE_URL;
const tenant = process.env.CEREBRUM_RELEASE_TENANT ?? 'meridian-demo';
const institution = process.env.CEREBRUM_RELEASE_INSTITUTION ?? 'meridian-logistics';
const releaseId = process.env.CEREBRUM_CANONICAL_RELEASE_ID ?? 'REL-CANONICAL-SIGNED';
const artifactDir = resolve(process.env.CEREBRUM_ARTIFACT_DIR ?? 'artifacts');
await mkdir(artifactDir, { recursive: true });
const pgModule = await import('../apps/control-plane-api/node_modules/pg/lib/index.js');
const { Pool } = pgModule.default ?? pgModule;
const admin = new Pool({ connectionString: adminUrl });
const app = new Pool({ connectionString: appUrl });
await admin.query("INSERT INTO institution_ir_candidates (tenant_id,institution_id,candidate_id,version,ir_hash,compiler_version,input_source_hashes,validation_findings,control_graph_diff,status,payload) VALUES ($1,$2,$3,'1','sha256:ir-canonical','compiler-v1','[\"sha256:source\"]'::jsonb,'[{\"status\":\"PASSED\",\"qualification_hash\":\"sha256:qualification\"}]'::jsonb,'{\"hash\":\"sha256:graph\"}'::jsonb,'QUALIFIED','{}'::jsonb) ON CONFLICT DO NOTHING", [tenant, institution, `CAND-${releaseId}`]);
await admin.query("INSERT INTO institution_releases (tenant_id,institution_id,release_id,candidate_id,version,status,lifecycle_state,manifest_hash,signature_status,signed_by,signed_at,payload) VALUES ($1,$2,$3,$4,1,'SIGNED','SIGNED','sha256:release-manifest','SIGNED','kms-key-v1',now(),$5::jsonb) ON CONFLICT DO NOTHING", [tenant, institution, releaseId, `CAND-${releaseId}`, JSON.stringify({ institutional_ir_hash: 'sha256:ir-canonical', source_manifest_hash: 'sha256:source', control_graph_hash: 'sha256:graph', compiler_version: 'compiler-v1', qualification_hash: 'sha256:qualification', release_manifest_hash: 'sha256:release-manifest', signing_key_id: 'kms-key-v1', signing_key_version: '1', signature: 'signed-test' })]);
const fields = [
  ['manifest_hash', 'institution_releases', "manifest_hash='sha256:tampered'"],
  ['institutional_ir', 'institution_releases', "payload=jsonb_set(payload,'{institutional_ir_hash}','\"sha256:tampered\"'::jsonb)"],
  ['source_hashes', 'institution_ir_candidates', "input_source_hashes='[\"tampered\"]'::jsonb"],
  ['compiler_version', 'institution_ir_candidates', "compiler_version='attacker'"],
  ['control_graph_diff', 'institution_ir_candidates', "control_graph_diff='\"tampered\"'::jsonb"],
  ['qualification_result', 'institution_ir_candidates', "validation_findings='[{\"status\":\"FAILED\"}]'::jsonb"],
  ['signature', 'institution_releases', "payload=jsonb_set(payload,'{signature}','\"tampered\"'::jsonb)"],
  ['signing_key_id', 'institution_releases', "payload=jsonb_set(payload,'{signing_key_id}','\"attacker\"'::jsonb)"],
  ['signing_key_version', 'institution_releases', "payload=jsonb_set(payload,'{signing_key_version}','\"999\"'::jsonb)"],
];
const results = [];
for (const [field, table, value] of fields) {
  const client = await app.connect();
  try { await client.query('BEGIN'); await client.query('SELECT set_config($1,$2,true)', ['app.tenant_id', tenant]); const where = table === 'institution_releases' ? 'tenant_id=$1 AND release_id=$2' : 'tenant_id=$1 AND candidate_id=(SELECT candidate_id FROM institution_releases WHERE tenant_id=$1 AND release_id=$2)'; await client.query(`UPDATE ${table} SET ${value} WHERE ${where}`, [tenant, releaseId]); await client.query('COMMIT'); results.push({ field, passed: false, outcome: 'mutation accepted' }); }
  catch (error) { await client.query('ROLLBACK'); results.push({ field, passed: true, outcome: String(error.code ?? 'POSTGRES_REJECTED') }); }
  finally { client.release(); }
}
const report = { qualification: 'signed-release-immutability-v1', release_id: releaseId, mutation_results: results, passed: results.length === fields.length && results.every(item => item.passed), completed_at: new Date().toISOString() };
await writeFile(resolve(artifactDir, 'release-immutability-validation.json'), JSON.stringify(report, null, 2));
await admin.end(); await app.end();
if (!report.passed) process.exitCode = 1;
