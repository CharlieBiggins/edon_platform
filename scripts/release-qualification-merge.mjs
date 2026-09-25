import { mkdir, readFile, writeFile } from 'node:fs/promises';
import { resolve } from 'node:path';
const dir = resolve(process.env.CEREBRUM_ARTIFACT_DIR ?? 'artifacts');
await mkdir(dir, { recursive: true });
const load = async name => JSON.parse(await readFile(resolve(dir, name), 'utf8'));
const [transition, faults, mutations, baseline, restart, restore] = await Promise.all([
  load('release-transition-validation.json'), load('release-transition-fault-validation.json'), load('release-immutability-validation.json'),
  load('release-digest-baseline.json'), load('release-digest-restart.json'), load('release-digest-restore.json'),
]);
const cases = [
  { name: 'HTTP transition validation', passed: transition.passed === true },
  { name: 'rollback injection', passed: faults.disposition === 'PASSED' && faults.checks.every(check => check.passed) },
  { name: 'signed-field mutation attacks', passed: mutations.passed === true && mutations.mutation_results.every(result => result.passed) },
  { name: 'restart canonical digest equality', passed: baseline.digest === restart.digest },
  { name: 'backup/restore canonical digest equality', passed: baseline.digest === restore.digest },
];
const report = {
  boundary: 'INSTITUTION_RELEASE_TRANSITION_V1',
  disposition: cases.every(item => item.passed) ? 'QUALIFIED' : 'FAILED',
  commit_sha: process.env.GITHUB_SHA ?? 'local',
  migration_versions: process.env.CEREBRUM_MIGRATION_VERSIONS?.split(',').filter(Boolean) ?? [],
  postgres_version: process.env.CEREBRUM_POSTGRES_VERSION ?? 'unknown',
  cases,
  canonical_hashes: { baseline: baseline.digest, restart: restart.digest, restore: restore.digest },
  generated_at: new Date().toISOString(),
};
await writeFile(resolve(dir, 'release-transition-qualification.json'), JSON.stringify(report, null, 2));
if (report.disposition !== 'QUALIFIED') process.exitCode = 1;
