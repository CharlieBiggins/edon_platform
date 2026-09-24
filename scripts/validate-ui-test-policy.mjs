import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..', 'command-center');
const files = [];
function walk(directory) {
  for (const entry of fs.readdirSync(directory, { withFileTypes: true })) {
    if (entry.name === 'node_modules' || entry.name === 'test-results' || entry.name.endsWith('-snapshots')) continue;
    const full = path.join(directory, entry.name);
    if (entry.isDirectory()) walk(full);
    else if (/\.(spec|test)\.(ts|tsx)$/.test(entry.name)) files.push(full);
  }
}
walk(root);
const failures = [];
for (const file of files) {
  const lines = fs.readFileSync(file, 'utf8').split(/\r?\n/);
  lines.forEach((line, index) => {
    if (/\b(?:test|it|describe|suite)\.only\s*\(/.test(line) || /\b(?:fit|fdescribe)\s*\(/.test(line)) failures.push(`${path.relative(root, file)}:${index + 1}: focused test is forbidden`);
    if (/\b(?:test|it|describe|suite)\.skip\s*\(/.test(line) || /\b(?:xit|xdescribe)\s*\(/.test(line)) {
      const context = lines.slice(Math.max(0, index - 2), index + 1).join('\n');
      const inlineReason = /\.skip\([^,]+,\s*['"`][^'"`]+['"`]\s*\)/.test(line);
      if (!/skip-reason:/i.test(context) && !inlineReason) failures.push(`${path.relative(root, file)}:${index + 1}: skipped test requires a reason comment or inline reason`);
    }
  });
}
if (process.env.CI && /update-snapshots|--update-snapshots/.test(process.argv.join(' '))) failures.push('snapshot updates are forbidden in CI; review and commit baselines locally');
if (failures.length) {
  console.error('UI test policy failed');
  for (const failure of failures) console.error(`::error::${failure}`);
  process.exitCode = 1;
} else {
  console.log(`UI test policy passed: ${files.length} test files scanned; no focused tests or undocumented skips.`);
}
