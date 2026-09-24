import { AppendOnlyJournal } from '../../../packages/platform-core/src/event-journal.js';
import { DeterministicKernel } from '../../../packages/platform-core/src/kernel.js';

/** Server boundary: authoritative services are instantiated here, never in browser code. */
export const controlPlaneBoundary = 'server-only' as const;
export const createControlPlaneServices = () => ({
  journal: new AppendOnlyJournal(),
  kernel: new DeterministicKernel(),
});
export { createControlPlaneServer } from './server.js';


