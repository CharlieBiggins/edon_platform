# Protocol

## Frozen components

- Base model: `Qwen/Qwen3-4B-Instruct-2507` at revision
  `cdbee75f17c01a7cc42f958dc650907174af0554`.
- Engineering model candidate: DEV-017 `continuation-step-24`, retained only
  because it had one fewer failing development case than step 12. DEV-017
  remains a negative scientific result.
- Gate: the unchanged 26-check full-regression gate.
- Training: prohibited; zero optimizer steps.

## Verification path

For each case, the model and deterministic executor receive the observation.
The executor does not receive the scorer record or expected answer. The
verifier accepts the model output only when all of these hold:

1. raw schema validity;
2. EOS termination;
3. no generation-limit hit; and
4. exact equality between model-compiled and executor-compiled outputs.

Otherwise the final hybrid output is the executor result. Each action,
differing path, and unsafe model `ALLOW` override is frozen in a per-case audit.

## Gates

Development consists of 64 fresh balanced cases. All 26 hybrid checks,
including zero unsafe authorizations, must pass before confirmation model
inference begins. Confirmation consists of 192 fresh balanced cases and is
single-use. Model-only results never determine passage.

## Next gate

A confirmation pass requires fresh-seed reproduction and an independently
implemented executor/verifier before any transfer claim can be considered.