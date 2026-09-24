# Platform package boundaries

- `packages/contracts`: browser-safe types and schemas only.
- `packages/platform-core`: server-only journal, evidence, Kernel, mandates, receipts and lifecycle logic.
- `packages/platform-testkit`: deterministic scenarios and validation harnesses.
- `apps/command-center`: frontend UI and API client boundary.
- `apps/control-plane-api`: server/API process boundary.
