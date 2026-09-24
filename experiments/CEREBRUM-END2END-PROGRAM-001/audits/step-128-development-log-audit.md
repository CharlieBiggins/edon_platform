# Program-001 step-128 development audit

Date: 2026-09-08. Status: raw-output diagnosis complete; all 128 logged evaluations reproduced.

## Evidence and scope

Source: workspace `prism-uploads/file.txt` (uploaded as `/prism-uploads/file.txt`).
Uploaded log SHA-256: `97280c265a21888727760895f2b2575a985ef040466f46790fe44e7c9c42c3e4`.
The log contains 128 evaluation records for `program-step-128`.

Reported input SHA-256: `43f6ed6a370b39f3a7e3bc8d2a5629cfad743a27d4c784a24e74ba517aaa8aaf`.
Reported prediction SHA-256: `ec4ed0878b97aac39ae7fda1cd53c44ed58e55b6e981f369f11353128172c480`.
Both byte hashes were independently verified against the corresponding files
in `prism-uploads/`. Both contain 128 unique, matching case IDs. The uploaded
prediction manifest agrees with the logged checkpoint, count and hashes.
Read-only replay through the local `scoring.evaluate` reproduced all 128 logged
evaluation dictionaries exactly, including every case-level field. This report
is not a replacement for the original run archive.

No experiment settings, original scores, predictions or training artifacts were
changed. No confirmation inputs or outcomes were inspected or generated.

## Outcome

Step 128 has 125/128 correct scored decisions and exact executed states,
115/128 exact programs and verifier acceptances, and 127/128 parseable outputs.
All 128 outputs have recorded EOS termination; no generation-limit hits occur.
The three reported unsafe-authorization counters are zero on this set.
The checkpoint passes all six registered baseline-improvement checks and nine
of eleven absolute checks. Event ordering and partition each score 115/128,
below their 0.95 floors. At N=128 each floor requires at least 122 successes.

The final run status remains `NO_PROGRAM_CANDIDATE_PASSES_DEVELOPMENT_GATE`;
confirmation remains sealed. This audit does not authorize promotion or transfer.

## Case inventory

Class O: complete event coverage, parser/scheduler/interpreter agreement, correct
decision, exact executed state, and exact derived/claimed certificates; ordering
and partition checks fail, causing rejection and full-program failure.

Class E: parsing and parser agreement succeed, but the generated approval event
identifier lacks its `event-` prefix. Both execution engines raise
`ValueError: unknown event identifier`. The verifier returns before attaching
the parsed program and completed execution results.

Class P: malformed STEP records replace the required state and certificate
claims; both parsers reject the output. Downstream checks remain false and the
scored decision is null.

| Case ID | Mechanism | Variant | Class | Scored decision / oracle |
|---|---|---|---|---|
| program-case-76014d12bdef555d | PRIORITY_RACE | BASE | E | null / ALLOW |
| program-case-7568411ec1cc63a3 | PRIORITY_RACE | INTERVENTION | E | null / DENY |
| program-case-a151e298015c15a7 | UNRESOLVED_APPEAL | BASE | O | ALLOW / ALLOW |
| program-case-9446bf2b5a9dc238 | UNRESOLVED_APPEAL | INTERVENTION | O | CONTESTED / CONTESTED |
| program-case-a49aa15898f25f82 | UNRESOLVED_APPEAL | BASE | O | ALLOW / ALLOW |
| program-case-5c580701997eb71c | UNRESOLVED_APPEAL | INTERVENTION | O | CONTESTED / CONTESTED |
| program-case-0ded1f9bb35e116c | DELAYED_EVIDENCE | INTERVENTION | O | ABSTAIN / ABSTAIN |
| program-case-04b3e1c202b14a4d | QUEUE_ORDER_AND_ACTOR_RENAME | BASE | O | ALLOW / ALLOW |
| program-case-baabcf3904e0db21 | UNRESOLVED_APPEAL | BASE | O | ALLOW / ALLOW |
| program-case-0062cb05f605a40a | UNRESOLVED_APPEAL | INTERVENTION | O | CONTESTED / CONTESTED |
| program-case-ccf880ceb82b769d | DELAYED_EVIDENCE | INTERVENTION | O | ABSTAIN / ABSTAIN |
| program-case-d69192b0df9e37eb | UNRESOLVED_APPEAL | INTERVENTION | P | null / CONTESTED |
| program-case-5a89fc72e31f3e1a | DELAYED_EVIDENCE | INTERVENTION | O | ABSTAIN / ABSTAIN |

Totals: O=10, E=2, P=1. By mechanism: unresolved appeal=7,
delayed evidence=3, priority race=2, queue order/actor rename=1.
All three incorrect scored decisions are null. Raw inspection now establishes
that the two class E outputs claim ALLOW and DENY, respectively, both matching
their oracles. The class P output contains no actual decision certificate.
These diagnostic observations do not change the registered 125/128 decision score.

## Scoring interpretation

In `ACTIONNET-DATA-QUAL-021-PROGRAM/program_ir.py`, `verify_program` defines
`partition_exact` as correct event ordering AND an exact disposition sequence.
Consequently, every ordering failure automatically fails partition. These are
not independent demonstrations of ordering and execute/defer errors. A per-event
disposition audit is needed to isolate any actual time-boundary mistakes.

For class O, exact state/certificate results do not make the submitted sequence
compliant with the registered program contract. Raw inspection confirms that
all ten cases assign every event the correct EXECUTE/DEFER disposition when
checked by event ID independently of position. Their partition failures arise
from the ordering dependency, not an observed disposition error.

In the local code, `parsed_program` is attached only after successful execution.
Thus an execution-stage early return can yield `actual_decision: null` even
when parsing succeeded. Downstream false flags can be uncomputed defaults,
not observed interpreter disagreements or independently wrong state claims.
Safety counters also default to false on early returns; the reported zeros
must not be described as a complete semantic safety assessment of failed outputs.

## Confirmed raw-output causes

### Six appeal ordering failures

Cases `a151e298015c15a7`, `9446bf2b5a9dc238`, `a49aa15898f25f82`,
`5c580701997eb71c`, `baabcf3904e0db21`, and `0062cb05f605a40a`
(all with the `program-case-` prefix) place OPEN_APPEAL after ADD_APPROVAL
and SET_ROUTE_ACCEPTED. These events share a timestamp, but OPEN_APPEAL has
priority 20 and must precede the other two, whose priority is 30.

In `9446bf2b5a9dc238`, the appeal also appears after evidence and resource
events at later times. In `0062cb05f605a40a`, it appears after a later evidence
event. All reordered events are EXECUTE events; the resulting states and
certificates nevertheless match their oracles in these particular cases.

### Three deferred-event ordering failures

In delayed-evidence cases `0ded1f9bb35e116c` and `5a89fc72e31f3e1a`,
SET_POLICY_ALLOWED (priority 5) is incorrectly placed after evidence status
(priority 20) and evidence receipt (priority 21) at the same timestamp.
In `ccf880ceb82b769d`, evidence receipt (priority 21) is incorrectly placed
before evidence status (priority 20). These misplaced events are all correctly
marked DEFER, so they do not change the executed state at the query time.

### One executed-event chronological inversion

Queue/rename case `04b3e1c202b14a4d` places the resource reservation event at
time 10 before the evidence receipt event at time 9. Both are correctly marked
EXECUTE, and the final state and certificate remain exact in this case.

### Two identifier-copy failures, not demonstrated priority-resolution failures

Both priority-race outputs replace the required identifier
`event-ede3cb4badbb7370` with `ede3cb4badbb7370`. The input prompts contain the
correct full identifier. Thus each generated program has one missing source
event ID and one unknown ID. Both parsers accept the syntax; both interpreters
raise `ValueError: unknown event identifier` when executing it.

The raw claimed decisions are correct (ALLOW for BASE, DENY for INTERVENTION),
but the original scorer does not extract them after an execution failure.
The demonstrated defect is identifier copying; the mechanism label alone
would have misleadingly suggested a priority-race reasoning error.

### One malformed claim section

Appeal case `d69192b0df9e37eb` ends its event steps with:

```text
STEP {"disposition":"CLAIM_STATE","event_id":"FINAL_STATE"}
STEP {"disposition":"CLAIM_CERTIFICATE","event_id":"FINAL_CERTIFICATE"}
END_ACTIONNET_TEMPORAL_PROGRAM
```

It supplies neither the required CLAIM_STATE object nor CLAIM_CERTIFICATE
object. Parser A reports `step value invalid`; parser B reports
`missing program claim`. This is a grammar/completion failure, not malformed
JSON within those two STEP payloads. The output ended with EOS and did not hit
the generation limit.

## Follow-up scope

The concrete repair targets are canonical sorting (including deferred events),
exact identifier copying, and complete grammar-compliant claims. A separately
registered follow-up can target these using training/development material,
with independent per-event disposition diagnostics to disentangle ordering
from time-boundary errors. The training intervention and fresh evaluation
design remain to be chosen; this audit does not implement them.

Do not change this run's thresholds, extend its training retroactively,
automatically sort its frozen outputs, or use its sealed confirmation set for
diagnosis. The original base raw predictions are still needed for the separate
baseline format/termination investigation, not for this completed 13-case audit.