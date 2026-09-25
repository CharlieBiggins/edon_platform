import { mkdir, writeFile } from 'node:fs/promises';
const base = process.env.CEREBRUM_STAGING_URL;
if (!base) throw new Error('CEREBRUM_STAGING_URL is required');
const checks = [];
for (const path of ['/healthz', '/readyz']) {
  const response = await fetch(`${base}${path}`); checks.push({ name: path, status: response.status, passed: response.ok }); if (!response.ok) throw new Error(`${path} returned ${response.status}`);
}
const report = { profile: 'STAGING', status: 'qualified-infrastructure-health', staging_url: base.replace(/\/\/.*@/, '//REDACTED@'), checks, production_dispatch: false, generated_at: new Date().toISOString(), simulated_surfaces: ['C1 reasoning', 'customer connectors', 'production dispatch'] };
await mkdir(process.env.ARTIFACT_DIR ?? 'artifacts', { recursive: true });
await writeFile(`${process.env.ARTIFACT_DIR ?? 'artifacts'}/staging-qualification.json`, JSON.stringify(report, null, 2));
