# Experiment registry

This is the human-readable index. `registry.json` is the machine-readable source.

| ID | Purpose | Status | Frozen result |
| --- | --- | --- | --- |
| `ACTIONNET-DATA-QUAL-001` | Original paired-trajectory qualification | Qualified | 29/29 controls |
| `ACTIONNET-DATA-QUAL-002` | Observable rendering repair | Qualified | 33/33 controls |
| `ACTIONNET-DATA-QUAL-003` | Multi-view repair qualification | Qualified | 23/23 controls |
| `ACTIONNET-DATA-QUAL-004` | Independent EventNet data qualification | Qualified | 31/31 controls |
| `ACTIONNET-DATA-QUAL-005` | Fresh compact structured-repair data | Qualified | 31/31 controls |
| `ACTIONNET-DATA-QUAL-006` | Appeal-boundary narrow-repair data | Qualified | 35/35 controls |
| `ACTIONNET-DATA-QUAL-007` | Execution-transfer repair data | Qualified | 37/37 controls |
| `ACTIONNET-DATA-QUAL-008` | Governed multi-domain authoring | Ready for expert authoring | 42/42 controls; zero training-eligible records |
| `ACTIONNET-DATA-QUAL-009` | Fresh multigeneration repair data | Qualified | 40/40 controls |
| `ACTIONNET-DATA-QUAL-010` | Queue-integrity and unresolved-appeal repair data | Qualified | 33/33 controls; 4,032 training and 192 validation records |
| `ACTIONNET-DATA-QUAL-011` | Failure-focused unresolved-appeal continuation data | Qualified | 27/27 controls; 768 training and 64 held-renderer validation certificates |
| `ACTIONNET-DATA-QUAL-012` | Balanced appeal-finality calibration data | Qualified | 28/28 controls; 384 symmetric-weight training and 64 fresh validation certificates |
| `ACTIONNET-DATA-QUAL-013` | Tight near-clock appeal-boundary selection data | Qualified | 29/29 controls; 192 train, 32 development-selection, and 64 untouched-confirmation certificates |
| `ACTIONNET-DATA-QUAL-014` | Fresh full multi-task regression data | Qualified | 31/31 controls; 192 held-renderer records, 48 per scored task, and no training split |
| `ACTIONNET-DATA-QUAL-015` | Mixed replay and fresh retention-regression data | Qualified | 37/37 controls; 384 train, 64 development-selection, and 192 untouched-confirmation records |
| `ACTIONNET-DATA-QUAL-016` | Fresh delayed-evidence and exact-state narrow-repair data | Qualified | 33/33 controls; 368 train, 64 development-selection, and 192 untouched-confirmation records |
| `ACTIONNET-DATA-QUAL-017` | Complete-exposure causal-chain curriculum | Qualified | 37/37 controls; 384 train, 64 development-selection, and 192 untouched-confirmation records |
| `ACTIONNET-DATA-QUAL-018` | Fresh target-blind verified-hybrid evaluation | Qualified | 33/33 controls; zero train, 64 development, and 192 single-use confirmation records |
| `ACTIONNET-DATA-QUAL-019` | Gold-intervention failure-localization matrix | Qualified | 34/34 controls; 32 scenarios under five cumulative diagnostic conditions and no training split |
| `ACTIONNET-DATA-QUAL-020` | Single-source interface calibration and decision-fidelity data | Qualified | 31/31 controls; 64 calibration and 64 disjoint heldout scenarios; zero training records |
| `CEREBRUM-DEV-001` | Initial ActionNet learning test | Completed; safety hold | 80.83% decision, 17 unsafe allows |
| `CEREBRUM-DEV-002` | Multi-task synthetic repair | Passed | 2/2 seeds pass internal gates |
| `CEREBRUM-TRANSFER-003` | Independent synthetic transfer | Failed gate | Partial signal; transfer not established |
| `CEREBRUM-DEV-003` | Multi-event queue development | Superseded | Seed 1 operator report failed exactness gates |
| `CEREBRUM-DEV-004` | Structured transition/queue repair | Completed; hold | Seed 1 passed; seed 2 passed 16/17 and failed the unresolved-appeal floor |
| `CEREBRUM-DEV-006` | Appeal-boundary learned repair | Ready to execute | Two registered seeds; no learned result yet |
| `CEREBRUM-DEV-009-RB1` | Compute-bounded two-seed cross-profile repair | Failed frozen gate | Both seeds completed; queue and unresolved-appeal safety gates failed |
| `CEREBRUM-DEV-010` | Fresh queue-integrity and appeal repair | Completed; failed two-seed gate | Seed 1 passed 26/26; seed 2 passed 24/26 with 0/2 unresolved appeals and one unsafe authorization |
| `CEREBRUM-DEV-011-FOCUSED` | Two-parent unresolved-appeal continuation diagnostic | First run completed; focused hold | Seed 26090512 passed 8/9: 32/32 unresolved, zero unsafe, but 30/32 resolved appeals; second run early-stopped |
| `CEREBRUM-DEV-012-FOCUSED` | Short balanced finality continuation | Completed; focused hold | Final checkpoint reached 59/64 but made one unsafe authorization; checkpoint 12 remained safe at 54/64 |
| `CEREBRUM-DEV-013-FOCUSED` | Safety-constrained near-clock checkpoint selection | Focused signal | Step 6 selected; untouched confirmation 63/64, zero unsafe, 9/9 checks |
| `CEREBRUM-DEV-014-FULL` | Frozen-candidate full multi-task regression | Completed; hold | 16/26 checks; zero unsafe, but transition and queue-state reconstruction failed |
| `CEREBRUM-DEV-015-MIXED` | Mixed multi-task retention continuation | Completed; development hold | Both checkpoints passed 23/26; one delayed-evidence unsafe authorization and two transition post-state misses; confirmation sealed |
| `CEREBRUM-DEV-016-NARROW` | Delayed-evidence safety and exact-state continuation | Completed; development hold | Both checkpoints passed 23/26 and shared all 12 failures; confirmation sealed |
| `CEREBRUM-DEV-017-CAUSAL` | Complete-exposure causal-chain continuation | Completed; development hold | Both checkpoints passed 18/26, retained two unsafe authorizations, shared 13 failures, and left confirmation sealed |
| `CEREBRUM-DEV-018-VERIFIED` | Frozen-model plus deterministic executor/verifier | Verified hybrid synthetic signal | 209/256 model outputs accepted; 47 overridden; 13 unsafe paths blocked; hybrid confirmation passed 26/26 |
| `CEREBRUM-DEV-019-DIAGNOSTIC` | Five-stage gold-intervention failure localization | Completed; instrument-validity hold | Raw decision accuracy 27/32; cumulative ordering support caused 11 decision degradations, so unique localization is unsupported |
| `CEREBRUM-DEV-020-INTERFACE-CALIBRATION` | Direct representation equivalence and immutable-certificate fidelity | Ready pending external lineage | 31/31 data and 21/21 core controls; 384 calibration predictions and conditional 192-prediction heldout stage; zero training |
| `CEREBRUM-TRANSFER-005` | Fresh protected generalization | Frozen; unauthorized | DEV-004 did not pass its two-seed prerequisite |
| `CEREBRUM-TRANSFER-006-EXPLORATORY` | Pre-repair synthetic transfer diagnostic | Ready to execute | 24/24 firewall and 5/5 readiness controls; unscored |
| `CEREBRUM-PLATFORM-CONTRIB-001` | Platform 002 matched contribution test | Proxy signal established; confirmatory Qwen blocked | Transparent proxy improves joint accuracy by 33.44 points; fresh independent custody and GPU runtime still required |
| `EDON-MLGW-OR-001` | Matched-resource Memphis storm-restoration operations-research program | Protocol ready; data and authorization blocked | 33/33 readiness controls and synthetic plumbing rehearsal only; no MLGW or Cerebrum performance result |
| `CEREBRUM-TRANSFER-008` | Compact two-seed zero-shot successor reservation for RB1 candidates | Reservation closed unmaterialized | RB1 failed its prerequisite; zero cases, labels, generator, runtime, predictions, scorer, or transfer result |
| `CEREBRUM-TRANSFER-010` | Independent-authorship EventNet successor reservation for DEV-010 candidates | Closed unmaterialized | DEV-010 failed its frozen prerequisite; 55/55 shell controls remain infrastructure evidence and no protected artifacts exist |
| `CEREBRUM-BUILD-001` | Engineering-first local-model Cerebrum program | Engineering shell ready; model execution not run | 27/27 readiness controls; Qwen/LoRA provider, fail-closed parsing, shadow-only runtime, and matched benchmark design; no trained Build-001 model or performance result |
| `CEREBRUM-CLOSED-LOOP-DEV-001` | Interactive learned closed-loop development curriculum | Ready for two-seed training | 288 training episodes, 2,496 supervised turns, 72 held-out development episodes, 624 label-separated validation turns, and a fail-closed executable environment; no learned result |
| `CEREBRUM-LATENT-COORD-001` | State-mediated coordination detection and governance | Protocol shell ready; candidate and protected instrument absent | Representation, baselines, 480-case reservation, causal gates, and custody defined; no capability result |
| `CEREBRUM-MINI-IGI-CAPSTONE-001` | Minimum internal bounded-IGI capstone across unseen institutional forms and learned closed loops | Shell ready; prerequisites unmet and materialization unauthorized | 58/58 readiness controls and 12/12 focused tests; 72 episodes, 36 pairs, three institutions, nine matched conditions, and zero protected artifacts or result |

## Mandatory package contract

Every major folder contains:

```text
README.md    what was tested and where the evidence lives
PROTOCOL.md  conditions, data boundary, metrics, and frozen gates
CLAIMS.md    supported, unsupported, provisional, and limitations
manifest.json artifact identity, hashes, lineage, storage, and scope
```

The ActionNet qualification packages are an explicit exception to the
manifest-only rule: their complete synthetic generators, generated public
development corpora, lineage, oracles, qualification results, and tests are
materialized here. Protected labels, adapters, checkpoints, real institutional
data, and temporary outputs remain outside Git.