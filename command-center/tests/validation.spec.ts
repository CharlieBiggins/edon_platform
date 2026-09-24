import AxeBuilder from '@axe-core/playwright';
import { expect, test } from './fixtures';

async function signIn(page: import('@playwright/test').Page) {
  await page.goto('/');
  const sso = page.getByRole('button', { name: /Continue with enterprise SSO/i });
  if (await sso.isVisible()) await sso.click();
  await expect(page.getByRole('banner')).toBeVisible();
}

async function openNav(page: import('@playwright/test').Page, name: string) {
  const menu = page.getByRole('button', { name: 'Open navigation', exact: true });
  if (await menu.isVisible()) await menu.click();
  await page.getByRole('navigation', { name: 'Primary navigation' }).getByRole('button', { name, exact: true }).click();
}

test.describe('governed Command Center validation', () => {
  test('@critical login and tenant-scoped incident entry', async ({ page }) => {
    await signIn(page);
    await expect(page.getByRole('heading', { name: 'Operations Overview' })).toBeVisible();
    await page.goto('/#/incident/INC-1042');
    await expect(page.getByRole('heading', { name: 'Memphis capacity disruption' })).toBeVisible();
    await expect(page.getByText(/SIMULATED ENVIRONMENT|SHADOW MODE/).first()).toBeVisible();
    await page.getByRole('button', { name: 'Ask Cerebrum', exact: true }).click();
    await expect(page.getByText(/No authorization or execution available/).first()).toBeVisible();
  });

  test('@critical shadow authority boundary prevents execution and bypass', async ({ page }) => {
    await signIn(page);
    await page.goto('/#/incident/INC-1042');
    await page.getByRole('button', { name: 'Ask Cerebrum', exact: true }).click();
    await expect(page.getByText(/Analysis only.*cannot authorize or execute/i)).toBeVisible();
    await expect(page.getByRole('button', { name: /Review selected scope/ })).toBeDisabled();
    await page.getByLabel('Demo persona').selectOption('Approver');
    await expect(page.getByRole('button', { name: /Review selected scope/ })).toBeEnabled();
    await expect(page.getByText(/SHADOW|simulated/i).first()).toBeVisible();
    await expect(page.getByRole('button', { name: /Execute|Dispatch|Approve action/i })).toHaveCount(0);
  });

  test('@critical role and permission matrix never exposes unauthorized review controls', async ({ page }) => {
    await signIn(page);
    await page.goto('/#/incident/INC-1042');
    const persona = page.getByLabel('Demo persona');
    for (const role of ['Operator', 'Auditor']) {
      await persona.selectOption(role);
      await expect(page.getByRole('button', { name: /Review selected scope/ })).toBeDisabled();
    }
    await expect(page.getByText(/Persona selection is not authentication/i)).toBeVisible();
    await persona.selectOption('Approver');
    await expect(page.getByRole('button', { name: /Review selected scope/ })).toBeEnabled();
  });

  test('@critical unqualified intelligence cannot be promoted to production', async ({ page }) => {
    await signIn(page);
    await page.goto('/#/intelligence');
    await expect(page.getByText(/Shadow only|not deployed|candidate/i).first()).toBeVisible();
    await expect(page.getByRole('button', { name: /Promote|Activate production|Deploy production/i })).toHaveCount(0);
  });

  test('@critical direct navigation, refresh and browser history preserve route state', async ({ page }) => {
    await signIn(page);
    await page.goto('/#/queue');
    await expect(page.getByRole('heading', { name: 'Work Queue', exact: true })).toBeVisible();
    await page.goto('/#/reconstructions');
    await expect(page.getByRole('heading', { name: 'Reconstructions', exact: true })).toBeVisible();
    await page.reload();
    await expect(page.getByRole('heading', { name: 'Reconstructions', exact: true })).toBeVisible();
    await page.goBack();
    await expect(page.getByRole('heading', { name: 'Work Queue', exact: true })).toBeVisible();
    await page.goForward();
    await expect(page.getByRole('heading', { name: 'Reconstructions', exact: true })).toBeVisible();
  });

  test('@critical Ask Cerebrum citations preserve evidence and restricted boundaries', async ({ page }) => {
    await signIn(page);
    await page.goto('/#/incident/INC-1042');
    await page.getByRole('button', { name: 'Ask Cerebrum', exact: true }).click();
    const ask = page.getByRole('dialog').first();
    await expect(ask).toContainText('Incident INC-1042');
    await ask.getByRole('button', { name: /What evidence is missing/ }).click();
    await expect(ask).toContainText('Evidence');
    await expect(ask).not.toContainText('restricted evidence payload');
  });

  test('@critical route states expose recoverable empty and restricted content', async ({ page }) => {
    await signIn(page);
    for (const route of ['#/', '#/overview', '#/queue', '#/reviews', '#/outcomes', '#/receipts', '#/value', '#/state', '#/integrations', '#/settings', '#/location', '#/actor', '#/reconstructions', '#/exceptions', '#/integrity', '#/holds', '#/exports', '#/builder', '#/intelligence']) {
      await page.goto(`/${route}`);
      await expect(page.locator('main')).toBeVisible();
      await expect(page.locator('main').getByRole('heading').first()).toBeVisible();
    }
    await openNav(page, 'Settings & Administration');
    await page.getByRole('button', { name: /^Authority & mandates/ }).click();
    await expect(page.getByText(/view only|Governed operation/i).first()).toBeVisible();
    await expect(page.getByRole('button', { name: 'Submit change proposal' }).first()).toBeVisible();
  });

  test('@critical accessibility has no automated WCAG violations', async ({ page }) => {
    await signIn(page);
    await page.goto('/#/incident/INC-1042');
    const result = await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag21aa']).analyze();
    expect(result.violations).toEqual([]);
  });

  test('Chat Focus and context drawers remain usable at supported widths', async ({ page }) => {
    await signIn(page);
    await page.goto('/#/incident/INC-1042');
    await page.getByRole('button', { name: 'Ask Cerebrum', exact: true }).click();
    const workspace = page.getByRole('dialog').first();
    const expand = workspace.getByRole('button', { name: /Expand workspace/ });
    if (await expand.count()) await expand.click();
    const full = page.getByRole('dialog').first().getByRole('button', { name: /Full investigation|Chat Focus/ });
    if (await full.count()) await full.click();
    const layoutMenu = page.getByText(/Layout · (Balanced|Analysis|Compact)/).first();
    if (await layoutMenu.count()) {
      await layoutMenu.click();
      await page.getByRole('button', { name: /Chat Focus · full width/ }).click();
    }
    await expect(page.locator('.context-rail').first()).toBeVisible();
    await expect(page.locator('.ask-workspace')).toBeVisible();
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
    const rail = page.locator('.context-rail').first();
    const icon = rail.locator('button').first();
    if (await icon.count()) {
      await icon.click();
      await expect(page.locator('.context-drawer').first()).toBeVisible();
      await page.keyboard.press('Escape');
    }
  });

  test('visual regression covers every Chat Focus context drawer', async ({ page }) => {
    await signIn(page);
    await page.goto('/#/incident/INC-1042');
    await page.getByRole('button', { name: 'Ask Cerebrum', exact: true }).click();
    const rail = page.locator('.context-rail').first();
    await expect(rail).toBeVisible();
    for (const label of ['Evidence', 'Timeline', 'Commitments', 'Plans', 'Control Graph', 'Decision', 'Outcome', 'Receipts']) {
      await rail.getByRole('button', { name: `Open ${label}` }).click();
      await expect(page.locator('.context-drawer')).toBeVisible();
      await expect(page).toHaveScreenshot(`drawer-${label.toLowerCase().replaceAll(' ', '-')}.png`, { fullPage: true, animations: 'disabled' });
      await page.keyboard.press('Escape');
    }
  });

  for (const width of [1920, 1440, 1100, 900]) {
    test(`visual smoke ${width}px`, async ({ page }, testInfo) => {
      await page.setViewportSize({ width, height: 1080 });
      await signIn(page);
      await page.goto('/#/incident/INC-1042');
      await expect(page.getByRole('heading', { name: 'Memphis capacity disruption' })).toBeVisible();
      await expect(page).toHaveScreenshot(`incident-${width}.png`, { fullPage: true, animations: 'disabled' });
      await page.getByRole('button', { name: 'Ask Cerebrum', exact: true }).click();
      await expect(page).toHaveScreenshot(`ask-docked-${width}.png`, { fullPage: true, animations: 'disabled' });
      if (testInfo.project.name === 'desktop') await expect(page).toHaveScreenshot(`ask-focus-${width}.png`, { fullPage: true, animations: 'disabled' });
    });
  }
});
