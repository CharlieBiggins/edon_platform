import { readFile, writeFile } from 'node:fs/promises';
import { createHash } from 'node:crypto';

const baseUrl = process.env.CEREBRUM_API_URL ?? 'http://127.0.0.1:8787';
const artifact = process.env.CEREBRUM_ARTIFACT_DIR ?? 'artifacts';
const baselinePath = `${artifact}/durability-baseline.json`;
const hash = value => createHash('sha256').update(JSON.stringify(value)).digest('hex');
async function get(path) {
  const response = await fetch(`${baseUrl}${path}`);
  if (!response.ok) throw new Error(`${path} returned HTTP ${response.status}`);
  const body = await response.json();
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
