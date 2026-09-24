# EDON-MLGW-OR-001

`EDON-MLGW-OR-001` is a protocol-ready operations-research program for testing
whether an EDON coordination layer could reduce electric-restoration outage
hours under matched storm damage, crews, inventory, tools, physical repair
times, safety constraints, and time-indexed information.

The initial event anchor is the Memphis bow-echo event beginning August 22,
2026. The current event is a **public-source development replay**, not a
protected or prospective result. A genuine prospective result requires a later
live shadow deployment whose controller, data contract, thresholds, and
analysis plan are frozen before outcomes occur.

This package is not affiliated with or authorized by Memphis Light, Gas and
Water. It contains no private MLGW data, detailed grid topology, switching
instructions, customer records, critical-facility locations, credentials, or
operational authority.

## Current status

`PROTOCOL_READY_BLOCKED_MISSING_MLGW_AUTHORIZATION_AND_AUTHORITATIVE_DATA`

The package includes:

- a frozen evidence taxonomy separating observed, derived, estimated, target,
  and pilot-measured values;
- append-only, hash-chained event capture and timeline freezing;
- schemas for sources, evidence, storm worlds, controller recommendations, and
  episode results;
- equal-information and equal-resource comparator contracts;
- deterministic replay and scoring utilities;
- actual-decision, heuristic, OR, general-agent, Cerebrum, and hybrid controller
  registrations;
- safety, custody, privacy, data-acquisition, statistical, historical-replay,
  live-shadow, and controlled-assistance plans;
- a synthetic integration rehearsal and deterministic tests.

## Validate the package

```bash
cd edon/experiments/EDON-MLGW-OR-001
python preflight.py
python -m unittest discover -s tests -v
python run_synthetic_rehearsal.py
```

The synthetic rehearsal verifies plumbing only. Its result must never be
reported as MLGW performance.

## When partnership data becomes available

1. Obtain written authorization and designate an independent data custodian.
2. Archive source bytes and internal exports by hash without committing
   protected material to Git.
3. Complete the data-readiness and simulator-calibration gates.
4. Freeze candidate and comparator runtimes before protected replay.
5. Execute the one-time protected scoring transaction.
6. Enter live shadow mode only after the protected replay threshold passes.

No controller in this package can execute a switch, dispatch a crew, or mutate
an operational system.