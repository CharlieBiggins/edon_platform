# Bound raw predictions — import contract, not a GPU runner

The five condition filenames are base, parent, ordinary, targeted, and
open_weight_alternative, each with `.jsonl`, `.binding.json`, `.manifest.json`.
All 48 records must follow `screen-inputs.jsonl` order; duplicate, blank, partial
or reordered records block scoring. A generation failure still counts as an
evaluated case: record its raw output and true generation flags. Do not drop it.

Each JSONL record requires:

```json
{"case_id":"FROM_INPUT","raw_output":"UNMODIFIED_MODEL_TEXT","ended_with_eos":true,"hit_generation_limit":false,"prompt_token_count":100,"generated_token_count":200,"generation_seconds":10.0}
```

Counts are example placeholders, not measured predictions. Boolean flags must
be JSON booleans. Token counts are positive integers <=4096. Timing is finite
and nonnegative. Inference is one uninterrupted response per case, greedy,
without retries or oracle access. Model-specific prompt wrappers and exact
runtime are declared in the registered interface, not patched after failures.

The exact binding object is produced by `run.prediction_binding(screen_dir,
registration, condition)` in a standalone CPU preparation process. Its fields:

- protocol_id;
- registration_sha256 (exact file bytes);
- condition;
- candidate (exact registered identity object);
- input_sha256 (label-free JSONL bytes);
- interface_sha256 (canonical JSON object hash of the interface contract).

The completion manifest is:

```json
{"binding":{},"count":48,"predictions_sha256":"sha256:REPLACE_WITH_ACTUAL_HASH","gpu_seconds":0.0,"cost_usd":0.0}
```

Fill the binding with the exact object, not an empty object. GPU seconds must
cover generation time and should include startup/model loading; cost must use
the actual billed/accounted rate. These are runner-reported measurements, not
independent attestations. Hardware/runtime/prompt/weights hashes must actually
be checked by the future runner: metadata written by an operator alone does
not prove that the specified model or runtime produced the outputs.

The importer preserves raw failures. A total budget overrun yields a HOLD
deviation while still reporting the completed screen. No partial-result score
is emitted. This package does not implement resumable GPU generation: do not
use it to repair or overwrite a partial remote JSONL. A future runner requires
separate tests for immutable bindings, archived partial tails, final manifests,
no concurrent writers, token qualification, actual runtime checks and cost stops.

`registration.json` binds the comparison code, inherited scorer source closure,
contract, cases, coverage report and predecessor audit. Keep its published hash
outside the mutable working folder before execution. Scoring reads those bytes
and never alters the registration or input. Replaying deterministic CPU scores
is allowed for audit, but not using partial scores to revise the instrument.