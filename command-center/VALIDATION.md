# Cerebrum UI validation

This is a **production-grade UI validation foundation**. It is not a claim that the complete UI is production-qualified: institutional data is still simulated, the initial unit suite is intentionally small, persistent staging is not yet available, and visual baselines require human approval.

The validation system has three layers:

- `npm run test:unit` runs Vitest and Testing Library component, browser-boundary and shared-contract checks.
- `npm run test:e2e:critical` runs the pull-request gate against Chromium. It covers login, tenant scope, governed review boundaries, C1 release restrictions, route states, Ask Cerebrum context and axe-core accessibility checks.
- `npm run test:e2e:all` runs the complete Playwright suite across the responsive and cross-browser projects. Visual baselines live in `tests/validation.spec.ts-snapshots` and cover 1920, 1440, 1100 and 900 pixel views plus all eight Chat Focus context drawers.

Playwright retains traces, screenshots and videos on failure. The custom fixture writes sanitized console and network failures to `failure-context.json`; bearer tokens and secret-like query values are redacted. CI uploads `test-results` and `playwright-report` for every job outcome.

The browser suite validates the prototype's governed boundaries. It does not replace server-side authorization, Kernel, OIDC, RLS, receipt-custody or shadow-execution tests. Those remain required gates in the Control Plane and staging workflows.

CI runs `test:policy` before browser tests. It rejects focused tests (`.only`), undocumented skips and snapshot-update commands. Screenshot baselines are generated locally, reviewed by a human, and committed; CI never updates them. `tests/coverage-matrix.json` records the intended route, role, mode, viewport and governed-journey coverage and is uploaded with every validation job.

The required branch-protection declaration is stored in `.github/branch-protection-required-checks.json`. Repository administrators must apply it to `master` so `PR critical UI validation` is required before merging.
