# Cerebrum Command Center — Phase 1 frontend prototype

A standalone React / TypeScript application using synthetic regional-logistics fixtures. It does not modify the frozen specification or connect to the EDON backend.

## Run

Requires Node.js 22.12+ (Node 24 recommended) and npm.

```powershell
cd D:\Cerebrum\edon_platform\command-center
npm ci
npm run dev
```

Open the local URL printed by Vite. Production bundle: `npm run build`; local bundle preview: `npm run preview`.

## Explore

- Start in the Memphis incident workspace; use Incident queue to search/filter and open other incidents.
- Compare three plans and inspect evidence, assurance, scope, shadow outcomes, and receipts.
- Open **Ask Cerebrum** for contextual questions. Expand into **Cerebrum Workspace** for plan/evidence analysis or enter full investigation mode; the conversation, incident, state version, and investigation objects persist across all three modes.
- In Cerebrum Workspace, Ask Cerebrum controls a separate operational canvas with Evidence, Timeline, Commitments, Plans, Control Graph, Decision, Outcome, and Receipts views. Each generated answer carries evidence, state, policy, and assumption provenance.
- Cerebrum Workspace uses **Comfortable** canvas density by default with an optional **Compact** setting. Ask Cerebrum retains its original conversation-focused visual density in every mode.
- Ask for a plan comparison to see interactive alternatives and run the read-only capacity simulation. Consequential language creates a simulated structured draft and routes back to the formal proposal workspace without authorizing or executing anything.
- Select the Approver **demo persona** to exercise scope review. A rationale and explicit acknowledgement are required. Review enters a simulated pending state before returning `SHADOW ONLY`.
- Use the scenario selector for loading, empty, stale, conflicted, restricted, degraded, and disconnected views. Loading is intentionally held until you complete the simulated load.
- Within the review dialog, “Simulate state change” closes review and disables it until the changed proposal is reviewed. The updated regional plan exceeds the local budget; local recovery is selected for fresh review.
- Open a challenge, correction, appeal, or scope-change request. Blocking requests invalidate earlier reviews. Simulated owner resolution preserves the original request and requires new review.
- Export clearly labeled simulated receipt JSON or Value Report CSV. Reset restores the original fixtures. Browser reload also discards session changes.

## Boundaries

All data, identity, roles, access restrictions, Kernel decisions, and review behavior are simulated. Persona selection and disabled frontend controls provide **no real authentication or authorization**. Restricted content is absent from the fixtures. No production execution, enterprise requests, model calls, credentials, actual signing, receipt verification, or persistence are implemented. No data is written to browser storage. The only network activity is serving local frontend assets and Vite's development connection.

The replay clock is fixed to 23 September 2026, America/Chicago (CDT). Shadow recommendations and historical operator records are separate fixtures. Report metrics are illustrative historical aggregates, not computed claims about this session. Estimated opportunity is not verified or realized savings.

## Structure

- `src/types.ts`: shared typed domain contracts.
- `src/data.ts`: public synthetic fixtures and formatting.
- `src/components.tsx`: reusable panels, badges, notices, metrics, dialogs, and export helpers.
- `src/Workspace.tsx`: plan comparison, evidence, assurance, authority, recourse, and shadow outcomes.
- `src/AskCerebrum.tsx`: docked Ask Cerebrum assistant plus the expanded/full-screen Cerebrum Workspace, reactive operational canvas, decision rail, and interactive Control Graph.
- `src/Pages.tsx`: queue, reviews, receipts, value, state, and connector views.
- `src/App.tsx`: shell, in-memory interactions, simulated review lifecycle, and hash navigation.
- `src/styles.css`: responsive desktop/tablet layouts, keyboard focus, reduced motion, and visual states.

## Verify

```powershell
npm run build
npm test
```

Playwright tests use installed Google Chrome and start their own local Vite server on port 4173. They cover desktop and tablet, version invalidation, scope ceilings, simulated review receipts, recourse resolution, all edge states, navigation, reporting, reconnect, all three Ask Cerebrum modes, structured-proposal guardrails, and accessibility. To use Playwright's bundled Chromium instead, remove `channel: 'chrome'` from the two projects and run `npx playwright install chromium`.
