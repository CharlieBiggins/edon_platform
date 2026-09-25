import { mkdir, readFile, writeFile } from 'node:fs/promises';
import { resolve } from 'node:path';
const dir = resolve(process.env.CEREBRUM_ARTIFACT_DIR ?? 'artifacts');
await mkdir(dir, { recursive: true });
const load = async name => JSON.parse(await readFile(resolve(dir, name), 'utf8'));
const required = ['institution-compiler-worker-cases.json', 'institution-compiler-qualification-baseline.json', 'institution-compiler-qualification-restart.json', 'institution-compiler-qualification-restore.json'];
const cases = [];
for (const name of required) {
  try { cases.push({ name, report: await load(name), passed: true }); } catch (error) { cases.push({ name, passed: false, error: error instanceof Error ? error.message : String(error) }); }
}
const worker = cases.find(item => item.name === required[0])?.report;
const baseline = cases.find(item => item.name === required[1])?.report;
const restart = cases.find(item => item.name === required[2])?.report;
const restore = cases.find(item => item.name === required[3])?.report;
const requiredCasesPassed = Boolean(worker?.disposition === 'PASSED' && worker.checks?.length && worker.checks.every(check => check.passed));
const baselinePassed = Boolean(baseline?.disposition === 'FAILED' ? false : baseline?.canonical_digest);
const equalityPassed = Boolean(baseline?.canonical_digest && restart?.canonical_digest === baseline.canonical_digest && restore?.canonical_digest === baseline.canonical_digest);
const report = { boundary: 'INSTITUTION_COMPILER_WORKER_V1', disposition: cases.every(item => item.passed) && requiredCasesPassed && baselinePassed && equalityPassed ? 'QUALIFIED' : 'FAILED', commit_sha: process.env.GITHUB_SHA ?? 'local', compiler_version: 'institution-compiler-v1', migration_versions: process.env.CEREBRUM_MIGRATION_VERSIONS?.split(',').filter(Boolean) ?? [], canonical_digest: baseline?.canonical_digest ?? null, required_cases: Object.fromEntries((worker?.checks ?? []).map(check => [check.name, check.passed ? 'PASSED' : 'FAILED'])), phase_reports: cases.map(item => ({ name: item.name, disposition: item.report?.disposition ?? 'MISSING' })), completed_at: new Date().toISOString() };
await writeFile(resolve(dir, 'institution-compiler-qualification-final.json'), JSON.stringify(report, null, 2));
console.log(JSON.stringify(report, null, 2));
if (report.disposition !== 'QUALIFIED') process.exitCode = 1;
