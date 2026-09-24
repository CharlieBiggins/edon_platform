import { readFile, writeFile } from 'node:fs/promises';
import { createHash } from 'node:crypto';
import { resolve } from 'node:path';
import { mkdir } from 'node:fs/promises';

const baseUrl = process.env.CEREBRUM_API_URL ?? 'http://127.0.0.1:8787';
const token = process.env.CEREBRUM_DURABILITY_TOKEN;
const expectedActor = process.env.CEREBRUM_DURABILITY_ACTOR ?? 'audit-01';
const expectedRole = process.env.CEREBRUM_DURABILITY_ROLE ?? 'auditor';
const expectedTenant = process.env.CEREBRUM_DURABILITY_TENANT ?? 'meridian-demo';
const artifact = resolve(process.env.CEREBRUM_ARTIFACT_DIR ?? 'artifacts');
await mkdir(artifact, { recursive: true });
const baselinePath = `${artifact}/durability-baseline.json`;
const hash = value => createHash('sha256').update(JSON.stringify(value)).digest('hex');
async function get(path) {
  const response = await fetch(`${baseUrl}${path}`, { headers: token ? { authorization: `Bearer ${token}` } : {} });
  const body = await response.json().catch(() => ({}));
  if (!response.ok) {
    const sanitized = body?.error ? { code: String(body.error.code ?? 'API_ERROR'), message: String(body.error.message ?? 'request failed') } : { body: String(JSON.stringify(body)).slice(0, 500) };
    throw new Error(JSON.stringify({ method: 'GET', path, status: response.status, error: sanitized, expected_actor: expectedActor, expected_role: expectedRole, expected_tenant: expectedTenant }));
  }
  if (!body.data) throw new Error(`${path} returned no data`);
  return body.data;
}
const reconstruction = await get('/v1/reconstructions/INC-1042');
const records = {
  proposal: await get('/v1/proposals/PROP-1042'),
  decision: await get('/v1/decisions/PROP-1042'),
  outcome: await get('/v1/outcomes/OUT-1042'),
  receipt: await get('/v1/receipts/RCP-1042'),
  state: await get('/v1/state/memphis-fulfillment'),
  reconstruction,
};
for (const [name, value] of Object.entries(records)) if (!value) throw new Error(`Missing ${name}`);
const current = { counts: { events: reconstruction.events.length }, hashes: Object.fromEntries(Object.entries(records).map(([name, value]) => [name, hash(value)])), state_version: records.state.version, reconstruction_hash: hash(reconstruction) };
if (process.env.DURABILITY_MODE === 'verify') {
  const baseline = JSON.parse(await readFile(baselinePath, 'utf8'));
  if (JSON.stringify(current) !== JSON.stringify(baseline)) throw new Error(`Durability mismatch: expected ${JSON.stringify(baseline)}, received ${JSON.stringify(current)}`);
}
await writeFile(process.env.DURABILITY_MODE === 'verify' ? `${artifact}/durability-verified.json` : baselinePath, JSON.stringify(current, null, 2));
