import { expect, test } from './fixtures';

test.describe('authenticated Institution Builder API workflow', () => {
  test('@critical compiles sources into a governed candidate and exposes failure boundaries', async ({ page }) => {
    let compiled = false;
    let sourceCount = 0;
    const candidate = { tenant_id: 'meridian-demo', institution_id: 'meridian-logistics', candidate_id: 'candidate-001', version: '1', ir_hash: 'sha256:ir-001', compiler_version: 'institution-compiler-v1', input_source_hashes: ['policy@1.0.0:sha256:source'], validation_findings: [], control_graph_diff: { added: [{ id: 'carrier-confirmation' }], changed: [], removed: [] }, status: 'VALIDATED', payload: { ir: { sources: [{ source_id: 'policy', source_version: '1.0.0', content_hash: 'sha256:source', objects: [{ type: 'policy' }] }] } } };
    await page.addInitScript(() => { (globalThis as { __CEREBRUM_API_MOCK__?: boolean }).__CEREBRUM_API_MOCK__ = true; });
    await page.route('**/v1/institutions/meridian-logistics/sources', async route => {
      if (route.request().method() === 'POST') { sourceCount += 1; await route.fulfill({ status: 201, contentType: 'application/json', body: JSON.stringify({ data: { tenant_id: 'meridian-demo', institution_id: 'meridian-logistics', source_id: 'policy', source_version: '1.0.0', owner_id: 'admin-01', provenance: 'operator-upload', sensitivity: 'internal', effective_from: '2026-01-01T00:00:00Z', content_hash: 'sha256:source', classification_status: 'CLASSIFIED', ingestion_timestamp: '2026-01-01T00:00:00Z', payload: {} }, meta: { correlation_id: 'test', contract_version: '2026-09-24.v1' } }) }); return; }
      await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ data: sourceCount ? [{ tenant_id: 'meridian-demo', institution_id: 'meridian-logistics', source_id: 'policy', source_version: '1.0.0', owner_id: 'admin-01', provenance: 'operator-upload', sensitivity: 'internal', effective_from: '2026-01-01T00:00:00Z', content_hash: 'sha256:source', classification_status: 'CLASSIFIED', ingestion_timestamp: '2026-01-01T00:00:00Z', payload: {} }] : [], meta: { correlation_id: 'test', contract_version: '2026-09-24.v1' } }) });
    });
    await page.route('**/v1/institution-compilations**', async route => {
      if (route.request().method() === 'POST') { compiled = true; await route.fulfill({ status: 202, contentType: 'application/json', body: JSON.stringify({ data: { institution_id: 'meridian-logistics', queued: true, status: 'COMPILATION_REQUESTED' }, meta: { correlation_id: 'test', contract_version: '2026-09-24.v1' } }) }); return; }
      await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ data: compiled ? { institution_id: 'meridian-logistics', status: 'COMPLETED', progress: { stage: 'VALIDATION', percent: 100 }, candidate_id: candidate.candidate_id, candidate } : { institution_id: 'meridian-logistics', status: 'COMPILATION_REQUESTED', progress: { stage: 'QUEUED', percent: 5 } }, meta: { correlation_id: 'test', contract_version: '2026-09-24.v1' } }) });
    });
    await page.goto('/');
    await page.getByRole('button', { name: /Continue with enterprise SSO/i }).click();
    await page.goto('/#/builder');
    await expect(page.getByRole('heading', { name: 'Compile Meridian Logistics' })).toBeVisible();
    await page.getByRole('button', { name: /Submit source/i }).click();
    await expect(page.getByText(/1 versioned/i)).toBeVisible();
    await page.getByRole('button', { name: /IR Mapping/i }).click();
    await page.getByRole('button', { name: /Request compilation/i }).click();
    await page.getByRole('button', { name: /Validation/i }).click();
    await expect(page.getByText('VALIDATED')).toBeVisible({ timeout: 5000 });
    await expect(page.getByText('sha256:ir-001')).toBeVisible();
    await page.getByRole('button', { name: /Control Graph/i }).click();
    await expect(page.getByText(/Inspectable diff/)).toBeVisible();
    await page.getByRole('button', { name: /Review & Sign/i }).click();
    await expect(page.getByText(/cannot sign or authorize/)).toBeVisible();
  });

  test('restricted and compiler failure responses remain visible and recoverable', async ({ page }) => {
    await page.addInitScript(() => { (globalThis as { __CEREBRUM_API_MOCK__?: boolean }).__CEREBRUM_API_MOCK__ = true; });
    await page.route('**/v1/institutions/meridian-logistics/sources', route => route.fulfill({ status: 403, contentType: 'application/json', body: JSON.stringify({ error: { code: 'PERMISSION_DENIED', message: 'Restricted source access denied', correlation_id: 'test' } }) }));
    await page.route('**/v1/institution-compilations**', route => route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ data: { institution_id: 'meridian-logistics', status: 'FAILED', progress: { stage: 'VALIDATION', percent: 80 }, error: 'Compiler validation failed' }, meta: { correlation_id: 'test', contract_version: '2026-09-24.v1' } }) }));
    await page.goto('/');
    await page.getByRole('button', { name: /Continue with enterprise SSO/i }).click();
    await page.goto('/#/builder');
    await expect(page.getByText('PERMISSION_DENIED')).toBeVisible();
    await expect(page.getByRole('button', { name: /Retry/i })).toBeVisible();
  });
});
