import { mkdir, writeFile } from 'node:fs/promises';

const baseUrl = process.env.CEREBRUM_API_URL ?? 'http://127.0.0.1:8787';
const started = new Date().toISOString();
const checks = [];
async function check(name, path) {
  try { const response = await fetch(`${baseUrl}${path}`); const body = await response.json(); const passed = response.ok; checks.push({ name, passed, detail: passed ? 'endpoint ready' : String(body?.error?.code ?? 'request failed') }); } catch (error) { checks.push({ name, passed: false, detail: 'API unavailable' }); }
}
await check('process health', '/healthz');
await check('runtime readiness', '/readyz');
const report = { profile: process.env.CEREBRUM_RUNTIME_PROFILE ?? 'STAGING_TEST', started_at: started, finished_at: new Date().toISOString(), passed: checks.every(check => check.passed), checks };
await mkdir('artifacts', { recursive: true });
await writeFile('artifacts/staging-validation.json', JSON.stringify(report, null, 2));
if (!report.passed) process.exitCode = 1;
