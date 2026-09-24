import { test as base } from '@playwright/test';
import fs from 'node:fs/promises';

function sanitize(value: string) {
  return value.replace(/Bearer\s+[^\s]+/gi, 'Bearer [redacted]').replace(/(password|token|secret|authorization)=?[^\s&]+/gi, '$1=[redacted]');
}

export const test = base.extend({
  page: async ({ page }, use, testInfo) => {
    const consoleErrors: string[] = [];
    const networkFailures: string[] = [];
    page.on('console', message => { if (message.type() === 'error') consoleErrors.push(sanitize(message.text())); });
    page.on('pageerror', error => consoleErrors.push(sanitize(error.message)));
    page.on('requestfailed', request => networkFailures.push(`${request.method()} ${sanitize(request.url())} ${request.failure()?.errorText ?? 'failed'}`));
    await use(page);
    if (testInfo.status !== testInfo.expectedStatus) {
      await fs.mkdir(testInfo.outputDir, { recursive: true });
      await fs.writeFile(testInfo.outputPath('failure-context.json'), JSON.stringify({ test: testInfo.title, status: testInfo.status, consoleErrors, networkFailures }, null, 2));
    }
  },
});

export { expect } from '@playwright/test';
