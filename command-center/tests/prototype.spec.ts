import { expect, test, type Page } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';

const reviewButton = (page: Page) => page.getByRole('button', { name: 'Review selected scope for simulated Kernel reevaluation' });
async function nav(page: Page, name: string) {
  const open = page.getByRole('button', { name: 'Open navigation', exact: true });
  if (await open.isVisible()) await open.click();
  await page.getByRole('navigation', { name: 'Primary navigation' }).getByRole('button', { name, exact: true }).click();
}
test.beforeEach(async ({ page }) => { await page.goto('/#/incident/INC-1042'); await expect(page.getByRole('heading', { name: 'Memphis capacity disruption' })).toBeVisible(); });

test('Operations Overview is the landing page above the detailed Work Queue', async ({ page }) => {
  await page.goto('/');
  await expect(page.getByRole('heading', { name: 'Operations Overview' })).toBeVisible();
  await expect(page.getByText('State v142 · updated 2 min ago', { exact: true })).toBeVisible();
  await expect(page.getByText('2 of 2 healthy', { exact: true })).toBeVisible();
  await expect(page.getByText('C1 shadow release 0.9.1', { exact: true })).toBeVisible();
  await expect(page.getByLabel('Cerebrum operating flow')).toContainText('Operations Overview');
  await expect(page.getByLabel('Cerebrum operating flow')).toContainText('Work Queue');
  await expect(page.getByLabel('Cerebrum operating flow')).toContainText('Cerebrum Workspace');
  await expect(page.getByLabel('Cerebrum operating flow')).toContainText('Decision');
  await expect(page.getByLabel('Cerebrum operating flow')).toContainText('Outcome');
  await page.getByRole('button', { name: /Open Work Queue/ }).click();
  await expect(page.getByRole('heading', { name: 'Work Queue', exact: true })).toBeVisible();
  await expect(page.getByRole('heading', { name: 'Work queue', exact: true })).toBeVisible();
});

test('Settings & Administration separates personal preferences from governed power', async ({ page }) => {
  await nav(page, 'Settings & Administration');
  await expect(page.locator('main').getByRole('heading', { name: 'Settings & Administration', exact: true, level: 1 })).toBeVisible();
  await expect(page.getByText('Environment', { exact: true }).last()).toBeVisible();
  await expect(page.getByText('SHADOW', { exact: true }).last()).toBeVisible();
  await expect(page.getByText('Personal preferences are configured. Institutional power is governed.', { exact: true }).first()).toBeVisible();
  await page.getByRole('button', { name: /Save preferences/ }).click();
  await expect(page.getByText('Saved for this simulated session', { exact: true })).toBeVisible();
  await page.getByRole('button', { name: /Authority & mandates/ }).click();
  await expect(page.getByText('Governed operation · view only', { exact: true })).toBeVisible();
  await expect(page.getByRole('button', { name: 'Submit change proposal' }).first()).toBeVisible();
  await expect(page.getByText('Proposed → Validated → Approval required → Authorized → Scheduled → Activated → Verified', { exact: true })).toBeVisible();
  await page.getByRole('button', { name: /^Environments/ }).click();
  await expect(page.getByText('No direct activation available', { exact: true })).toBeVisible();
  await expect(page.getByText('Execution mode: SHADOW', { exact: false })).toHaveCount(0);
  await page.getByRole('button', { name: /^Integrations/ }).last().click();
  await expect(page.getByText('Read-only connector health', { exact: true })).toBeVisible();
  await expect(page.getByText('Credentials, write scopes and activation are unavailable in this prototype.', { exact: true })).toBeVisible();
  await page.getByRole('button', { name: /Audit & change history/ }).click();
  await expect(page.getByText('Append-only simulated history', { exact: true })).toBeVisible();
});

test('universal scope drills from the network overview to a facility and actor inspector', async ({ page }) => {
  await nav(page, 'Operations Overview');
  await page.getByLabel('Operational scope').selectOption('facility');
  await expect(page.getByLabel('Operational scope')).toHaveValue('facility');
  await page.getByRole('button', { name: /Memphis fulfillment.*Capacity constrained/i }).click();
  await expect(page.getByRole('heading', { name: 'Memphis Fulfillment', exact: true })).toBeVisible();
  await expect(page.getByText('Meridian Logistics').first()).toBeVisible();
  await expect(page.getByText('Mid-South Network').first()).toBeVisible();
  await expect(page.getByRole('button', { name: /ROUTING-AGENT-07/ })).toBeVisible();
  await page.getByRole('button', { name: /ROUTING-AGENT-07/ }).click();
  await expect(page.getByRole('heading', { name: /ROUTING-AGENT-07/ })).toBeVisible();
  await expect(page.getByText('Write authority', { exact: true })).toBeVisible();
  await expect(page.getByText('Route recovery proposals only', { exact: true })).toBeVisible();
  await page.getByRole('tab', { name: 'Tools' }).click();
  await expect(page.getByText('reservation.create', { exact: true })).toBeVisible();
  await expect(page.getByText('Denied', { exact: true })).toBeVisible();
  await page.getByRole('tab', { name: 'Authority' }).click();
  await expect(page.getByText('No write authority', { exact: true })).toBeVisible();
});

test('workspace is simulated, responsive, and the three alternatives change the exact scope', async ({ page }, testInfo) => {
  const errors: string[] = []; page.on('pageerror', e => errors.push(e.message));
  await expect(page.getByText('SIMULATED ENVIRONMENT', { exact: true })).toBeVisible();
  await expect(page.getByRole('radio')).toHaveCount(3);
  await expect(reviewButton(page)).toBeDisabled();
  await page.getByLabel('Demo persona').selectOption('Approver');
  await expect(reviewButton(page)).toBeEnabled();
  await page.getByRole('radio', { name: 'Full network transfer Faster recovery' }).check();
  await expect(page.getByText('ESCALATION REQUIRED', { exact: true })).toBeVisible();
  await expect(reviewButton(page)).toBeDisabled();
  await page.getByRole('radio', { name: 'Local recovery Lower cost' }).check();
  await expect(reviewButton(page)).toBeEnabled();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
  await page.screenshot({ path: testInfo.outputPath('workspace.png'), fullPage: true });
  expect(errors).toEqual([]);
});

test('scope review produces an unsigned simulated receipt and never executes', async ({ page }) => {
  await page.getByLabel('Demo persona').selectOption('Approver');
  await reviewButton(page).click();
  const dialog = page.getByRole('dialog');
  const submit = dialog.getByRole('button', { name: 'Submit scope review for simulated reevaluation' });
  await expect(submit).toBeDisabled();
  await dialog.getByLabel('Review rationale').fill('Accept this exact scope for shadow comparison; capacity confirmation remains required.');
  await dialog.getByRole('checkbox').check();
  await submit.click();
  await expect(page.getByRole('button', { name: 'Shadow review recorded' })).toBeVisible();
  await page.getByRole('button', { name: 'View receipt', exact: true }).click();
  await expect(page.getByRole('dialog').getByText('Illustrative only / unsigned', { exact: true })).toBeVisible();
  await expect(page.getByRole('dialog').getByText('Simulated disposition / not executed', { exact: true })).toBeVisible();
  const download = page.waitForEvent('download');
  await page.getByRole('button', { name: 'Export simulated receipt' }).click();
  expect((await download).suggestedFilename()).toMatch(/^SIM-RCP-/);
  await page.keyboard.press('Escape');
  await expect(page.getByRole('dialog')).not.toBeVisible();
});

test('state change during review invalidates it and updates the new plan scope', async ({ page }) => {
  await page.getByLabel('Demo persona').selectOption('Approver');
  await reviewButton(page).click();
  await page.getByRole('button', { name: 'Simulate state change', exact: true }).click();
  await expect(reviewButton(page)).toBeDisabled();
  await page.getByRole('button', { name: 'Acknowledge', exact: true }).click();
  await expect(page.getByText('Acknowledged · unresolved')).toBeVisible();
  await expect(reviewButton(page)).toBeDisabled();
  await page.getByRole('button', { name: 'Refresh state and review changed plans' }).click();
  await expect(page.getByRole('radio', { name: 'Local recovery Lower cost' })).toBeChecked();
  await page.getByRole('radio', { name: 'Regional rebalance Recommended' }).check();
  await expect(page.getByText('ESCALATION REQUIRED', { exact: true })).toBeVisible();
  await expect(reviewButton(page)).toBeDisabled();
});

test('blocking evidence challenge preserves history and requires fresh review after resolution', async ({ page }) => {
  await page.getByRole('button', { name: 'Correct, challenge or escalate' }).click();
  await page.getByLabel('Request type').selectOption('Challenge evidence');
  await page.getByLabel('Supporting evidence and requested resolution').fill('EV-2083 capacity report conflicts with the warehouse count; request an owner reconciliation.');
  await page.getByRole('button', { name: 'Record simulated request and receipt' }).click();
  await expect(page.getByText('Open recourse blocks further review.', { exact: true })).toBeVisible();
  await page.getByLabel('Demo persona').selectOption('Approver');
  await expect(reviewButton(page)).toBeDisabled();
  await page.getByRole('button', { name: 'Simulate owner resolution; require new review' }).click();
  await expect(reviewButton(page)).toBeEnabled();
  await expect(page.getByText('Resolved', { exact: true })).toBeVisible();
  await nav(page, 'Decision receipts');
  await expect(page.getByText('Challenge evidence', { exact: true })).toBeVisible();
  await expect(page.getByText('Owner resolution recorded', { exact: true })).toBeVisible();
});

test('all operational edge states have meaningful views and restricted content stays omitted', async ({ page }) => {
  await page.getByLabel('Demo persona').selectOption('Approver');
  for (const scenario of ['conflicted', 'degraded', 'disconnected']) {
    await page.getByLabel('Demo scenario').selectOption(scenario);
    await expect(reviewButton(page)).toBeDisabled();
    await expect(page.locator('.safety-rail')).toBeVisible();
  }
  await page.getByLabel('Demo scenario').selectOption('restricted');
  await expect(page.getByRole('heading', { name: 'This record is outside your simulated access scope' })).toBeVisible();
  await expect(page.getByRole('radio')).toHaveCount(0);
  await page.getByLabel('Demo scenario').selectOption('loading');
  await expect(page.getByRole('status', { name: 'Loading simulated workspace' })).toBeVisible();
  await page.getByRole('button', { name: 'Complete simulated load' }).click();
  await page.getByRole('tab', { name: 'Evidence & state' }).click();
  await page.getByRole('button', { name: /Customer contract attachment/ }).click();
  await expect(page.getByRole('dialog').getByText('Restricted content is not included in this frontend fixture.')).toBeVisible();
  await expect(page.getByRole('button', { name: 'Challenge this evidence' })).toHaveCount(0);
  await page.keyboard.press('Escape');
  await page.getByLabel('Demo scenario').selectOption('empty');
  await expect(page.getByRole('heading', { name: 'No incidents to display' })).toBeVisible();
});

test('queue search opens distinct incidents; reporting and connectors are interactive', async ({ page }) => {
  await nav(page, 'Work Queue 3');
  await expect(page.getByText('4 incident records', { exact: false }).first()).toBeVisible();
  await expect(page.getByText('3 active', { exact: false }).first()).toBeVisible();
  await expect(page.getByText('$287K', { exact: true })).toBeVisible();
  await expect(page.getByText('Range $250K–$325K · not a verified loss', { exact: true })).toBeVisible();
  await expect(page.getByRole('columnheader', { name: 'Decision deadline' })).toBeVisible();
  await expect(page.getByRole('columnheader', { name: 'Cost of delay' })).toBeVisible();
  await expect(page.getByRole('columnheader', { name: 'State freshness' })).toBeVisible();
  await expect(page.getByRole('columnheader', { name: 'Next required action' })).toBeVisible();
  await expect(page.getByRole('button', { name: /1 review required Memphis decision expires in 23 minutes Review proposal/ })).toBeVisible();
  await page.getByLabel('Search incidents').fill('Nashville');
  await page.getByRole('button', { name: 'Open INC-1041', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Nashville carrier delay' })).toBeVisible();
  await nav(page, 'Shadow & outcomes');
  await expect(page.getByRole('heading', { name: 'Outcome comparison' })).toBeVisible();
  await nav(page, 'Value report');
  await page.getByLabel('Report period').selectOption('This month');
  await expect(page.getByText('$146.2k', { exact: true })).toBeVisible();
  await nav(page, 'Integrations');
  await page.getByRole('button', { name: 'Simulate connection interruption' }).first().click();
  await expect(page.getByRole('heading', { name: 'Synchronization interrupted' })).toHaveCount(2);
  await page.getByRole('button', { name: 'Simulate authenticated reconnect & resync' }).first().click();
  await expect(page.getByRole('heading', { name: 'Healthy simulation' })).toHaveCount(2);
});

test('shell separates environment, workflow mode, execution, and prototype controls', async ({ page }) => {
  await expect(page.getByText('Environment: SIMULATED', { exact: true })).toBeVisible();
  await expect(page.getByText('Workflow mode: SHADOW', { exact: true })).toBeVisible();
  await expect(page.getByText('Execution: DISABLED', { exact: true })).toBeVisible();
  const controls = page.locator('[data-prototype-only="true"]');
  await expect(controls.getByText('PROTOTYPE CONTROLS', { exact: true })).toBeVisible();
  await expect(controls.getByText('Demo-only toolbar · omitted from customer deployments', { exact: true })).toBeVisible();
});

test('Ask Cerebrum preserves context through docked, expanded, and investigation modes', async ({ page }) => {
  await page.getByRole('button', { name: 'Ask Cerebrum', exact: true }).click();
  const ask = page.getByRole('dialog', { name: 'Ask Cerebrum docked workspace' });
  await expect(ask.getByText(/Mid-South Network.*INC-1042/).first()).toBeVisible();
  await expect(ask.getByText('State v142', { exact: true }).first()).toBeVisible();
  expect(await ask.evaluate(element => element.querySelector('.ask-header')!.scrollWidth <= element.querySelector('.ask-header')!.clientWidth)).toBe(true);
  expect(await ask.evaluate(element => element.querySelector('.workspace-incident-header')!.scrollWidth <= element.querySelector('.workspace-incident-header')!.clientWidth)).toBe(true);
  await ask.getByLabel('Ask about current institutional context').fill('Why is human approval required?');
  await ask.getByRole('button', { name: 'Send question' }).click();
  await expect(ask.getByText(/assigned agent mandate permits only \$10,000/)).toBeVisible();
  await ask.getByRole('button', { name: 'Expand workspace' }).click();
  const expanded = page.getByRole('dialog', { name: 'Cerebrum Workspace expanded' });
  await expect(expanded).toHaveClass(/density-comfortable/);
  await expanded.getByRole('button', { name: 'Density: Comfortable' }).click();
  await expect(expanded).toHaveClass(/density-compact/);
  await expanded.getByRole('button', { name: 'Density: Compact' }).click();
  await expect(expanded).toHaveClass(/density-comfortable/);
  await expect(expanded.getByText('CEREBRUM WORKSPACE', { exact: true })).toBeVisible();
  await expect(expanded.getByText('ASK CEREBRUM', { exact: true }).first()).toBeVisible();
  await expect(expanded.getByText('No authorization or execution available', { exact: true })).toBeVisible();
  await expect(expanded.getByRole('tab', { name: 'Decision' })).toHaveAttribute('aria-selected', 'true');
  await expect(expanded.getByRole('paragraph').filter({ hasText: 'Why is human approval required?' })).toBeVisible();
  await expanded.getByLabel('Ask about current institutional context').fill('Compare recovery plans');
  await expanded.getByRole('button', { name: 'Send question' }).click();
  await expect(expanded.getByText('Plan comparison', { exact: true }).first()).toBeVisible();
  await expanded.getByRole('button', { name: 'Run simulation' }).click();
  await expect(expanded.getByText(/Regional rebalance becomes infeasible/)).toBeVisible();
  await expanded.getByRole('button', { name: 'Full investigation' }).click();
  const full = page.getByRole('dialog', { name: 'Cerebrum Workspace full investigation' });
  await expect(full.getByText('Memphis capacity disruption', { exact: true }).first()).toBeVisible();
  await expect(full.getByRole('paragraph').filter({ hasText: 'Why is human approval required?' })).toBeVisible();
  await expect(full.getByRole('tab', { name: 'Control Graph' })).toBeVisible();
  await expect(full.getByRole('button', { name: 'Generate briefing' })).toBeVisible();
  await expect(full.getByRole('complementary', { name: 'Persistent decision status' })).toContainText('23 MIN');
  await expect(full.getByRole('button', { name: 'Approve', exact: true })).toHaveCount(0);
  await full.getByLabel('Ask about current institutional context').fill('Which commitments are affected?');
  await full.getByRole('button', { name: 'Send question' }).click();
  await expect(full.getByRole('tab', { name: 'Commitments' })).toHaveAttribute('aria-selected', 'true');
  await full.getByLabel('Ask about current institutional context').fill('What happened afterward?');
  await full.getByRole('button', { name: 'Send question' }).click();
  await expect(full.getByRole('tab', { name: 'Outcome' })).toHaveAttribute('aria-selected', 'true');
  await full.getByLabel('Ask about current institutional context').fill('Show the dependency chain');
  await full.getByRole('button', { name: 'Send question' }).click();
  await expect(full.getByRole('tab', { name: 'Control Graph' })).toHaveAttribute('aria-selected', 'true');
  await full.getByRole('button', { name: /Carrier evidence missing/ }).click();
  await expect(full.getByText('EV-2085 · Missing', { exact: true })).toBeVisible();
  await full.getByRole('button', { name: 'Zoom in' }).click();
  await expect(full.getByText('110%', { exact: true })).toBeVisible();
  const accessibility = await new AxeBuilder({ page }).include('.ask-shell').withTags(['wcag2a', 'wcag2aa', 'wcag21aa']).analyze();
  expect(accessibility.violations).toEqual([]);
});

test('shared Workspace shell contains every operational tab above the decision rail at target viewports', async ({ page }, testInfo) => {
  test.skip(testInfo.project.name !== 'desktop', 'The viewport matrix is exercised once in the desktop browser project.');
  const nativeViewports = [
    { width: 1366, height: 768, label: '1366x768' },
    { width: 1440, height: 900, label: '1440x900' },
    { width: 1920, height: 1080, label: '1920x1080' },
  ];
  const layouts = [
    ...nativeViewports,
    ...nativeViewports.map(({ width, height, label }) => ({
      width: Math.floor(width / 1.25),
      height: Math.floor(height / 1.25),
      label: `${label} at 125% zoom-equivalent CSS viewport`,
    })),
  ];
  const tabs = ['Evidence', 'Timeline', 'Commitments', 'Plans', 'Control Graph', 'Decision', 'Outcome', 'Receipts'];

  for (const layout of layouts) {
    await page.setViewportSize({ width: layout.width, height: layout.height });
    await page.goto('/');
    await page.getByRole('banner').getByRole('button', { name: 'Ask Cerebrum', exact: true }).click();
    await page.getByRole('dialog', { name: 'Ask Cerebrum docked workspace' }).getByRole('button', { name: 'Expand workspace' }).click();
    await page.getByRole('dialog', { name: 'Cerebrum Workspace expanded' }).getByRole('button', { name: 'Full investigation' }).click();
    const workspace = page.getByRole('dialog', { name: 'Cerebrum Workspace full investigation' });
    await expect(workspace).toBeVisible();
    await page.waitForTimeout(300);

    for (const name of tabs) {
      const tab = workspace.getByRole('tab', { name, exact: true });
      await tab.click();
      await expect(tab, `${name} selected at ${layout.label}`).toHaveAttribute('aria-selected', 'true');
      const geometry = await workspace.evaluate(shell => {
        const rect = (selector: string) => {
          const element = shell.querySelector(selector);
          if (!(element instanceof HTMLElement)) throw new Error(`Missing ${selector}`);
          const box = element.getBoundingClientRect();
          return { top: box.top, right: box.right, bottom: box.bottom, left: box.left, width: box.width, height: box.height };
        };
        const main = rect('.ask-workspace');
        const conversation = rect('.ask-conversation');
        const messages = rect('.ask-messages');
        const composer = rect('.ask-composer-region');
        const canvas = rect('.ask-inspector');
        const tabNavigation = rect('.ask-inspector-tabs');
        const tabBody = rect('.ask-inspector-body');
        const rail = rect('.decision-rail');
        const shellBox = shell.getBoundingClientRect();
        return {
          shell: { top: shellBox.top, bottom: shellBox.bottom, width: shellBox.width, height: shellBox.height },
          rows: getComputedStyle(shell).gridTemplateRows.split(' ').length,
          main,
          conversation,
          messages,
          composer,
          canvas,
          tabNavigation,
          tabBody,
          rail,
          mainOverflow: getComputedStyle(shell.querySelector('.ask-workspace')!).overflow,
          conversationOverflow: getComputedStyle(shell.querySelector('.ask-conversation')!).overflow,
          canvasOverflow: getComputedStyle(shell.querySelector('.ask-inspector')!).overflow,
          messagesOverflowY: getComputedStyle(shell.querySelector('.ask-messages')!).overflowY,
          tabBodyOverflowY: getComputedStyle(shell.querySelector('.ask-inspector-body')!).overflowY,
        };
      });

      expect(geometry.rows, `five shell rows at ${layout.label}`).toBe(5);
      expect(geometry.shell.height, `100dvh shell at ${layout.label}`).toBeCloseTo(layout.height, 0);
      expect(geometry.mainOverflow).toBe('hidden');
      expect(geometry.conversationOverflow).toBe('hidden');
      expect(geometry.canvasOverflow).toBe('hidden');
      expect(geometry.messagesOverflowY).toBe('auto');
      expect(geometry.tabBodyOverflowY).toBe('auto');
      expect(geometry.conversation.left).toBeGreaterThanOrEqual(geometry.main.left - 1);
      expect(geometry.conversation.right).toBeLessThanOrEqual(geometry.canvas.left + 1);
      expect(geometry.canvas.right).toBeLessThanOrEqual(geometry.main.right + 1);
      expect(geometry.messages.bottom).toBeLessThanOrEqual(geometry.composer.top + 1);
      expect(geometry.composer.bottom, `composer contained at ${layout.label}`).toBeLessThanOrEqual(geometry.main.bottom + 1);
      expect(geometry.tabNavigation.bottom).toBeLessThanOrEqual(geometry.tabBody.top + 1);
      expect(geometry.tabBody.bottom, `${name} body contained at ${layout.label}`).toBeLessThanOrEqual(geometry.main.bottom + 1);
      expect(geometry.main.bottom, `main ends before rail at ${layout.label}`).toBeLessThanOrEqual(geometry.rail.top + 1);
      expect(geometry.rail.bottom, `rail contained at ${layout.label}`).toBeLessThanOrEqual(geometry.shell.bottom + 1);
    }
  }
});

test('Ask Cerebrum converts consequential language into an unauthorized structured draft', async ({ page }) => {
  await page.getByRole('button', { name: 'Ask Cerebrum', exact: true }).click();
  const ask = page.getByRole('dialog', { name: 'Ask Cerebrum docked workspace' });
  await ask.getByLabel('Ask about current institutional context').fill('Move everything to Nashville and spend up to $50,000.');
  await ask.getByRole('button', { name: 'Send question' }).click();
  await expect(ask.getByText('I can prepare that proposal, but I cannot authorize it.', { exact: false })).toBeVisible();
  await expect(ask.getByText('No authority granted', { exact: true })).toBeVisible();
  await expect(ask.getByText('DRAFT · SIMULATED', { exact: true })).toBeVisible();
  await ask.getByRole('button', { name: 'Review structured proposal' }).click();
  await expect(page.getByRole('dialog', { name: /Cerebrum|Ask Cerebrum/ })).toHaveCount(0);
  await expect(page.getByRole('tab', { name: 'Decision workspace' })).toHaveAttribute('aria-selected', 'true');
  await expect(page.getByText('Structured draft opened in the formal proposal workspace.', { exact: false })).toBeVisible();
});

test('docked Ask Cerebrum keeps message history independently scrollable', async ({ page }) => {
  await page.getByRole('button', { name: 'Ask Cerebrum', exact: true }).click();
  const ask = page.getByRole('dialog', { name: 'Ask Cerebrum docked workspace' });
  const summary = ask.getByRole('button', { name: 'Summarize this incident' });
  for (let index = 0; index < 4; index += 1) await summary.click();
  const history = ask.getByRole('region', { name: 'Ask Cerebrum conversation history' });
  expect(await history.evaluate(element => element.scrollHeight > element.clientHeight)).toBe(true);
  await history.evaluate(element => element.scrollTo({ top: element.scrollHeight }));
  expect(await history.evaluate(element => element.scrollTop)).toBeGreaterThan(0);
  await history.focus();
  await page.keyboard.press('Home');
  await expect(history).toBeFocused();
});

test('keyboard tabs, dialog focus, and core accessibility checks', async ({ page }) => {
  await page.getByRole('tab', { name: 'Decision workspace' }).focus();
  await page.keyboard.press('ArrowRight');
  await expect(page.getByRole('tab', { name: 'Evidence & state' })).toBeFocused();
  await expect(page.getByRole('tab', { name: 'Evidence & state' })).toHaveAttribute('aria-selected', 'true');
  const workspace = await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag21aa']).analyze();
  expect(workspace.violations).toEqual([]);
  await page.getByRole('tab', { name: 'Decision workspace' }).click();
  await page.getByLabel('Demo persona').selectOption('Approver');
  await reviewButton(page).click();
  const dialog = await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag21aa']).analyze();
  expect(dialog.violations).toEqual([]);
  await page.keyboard.press('Escape');
  await expect(reviewButton(page)).toBeFocused();
});
