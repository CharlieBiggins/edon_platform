# CPU build validation — September 8, 2026

Status: implementation and CPU validation complete; GPU execution not started.

- 18 tests pass locally and in an isolated extraction of the handoff ZIP.
- All 1,024 training and 128 development oracle programs pass independent
  parsing and execution verification.
- Repeating preparation preserves the registration and prepared files byte-for-byte.
- No case, pair, or semantic-family ID overlaps the uploaded Program-001
  development set. The new namespace and reserved ranges exclude its other splits.
- Confirmation data remains unmaterialized; no confirmation access record exists.
- No adapter artifacts or GPU training results have been produced.
- The bundle includes required Python source dependencies but no predecessor
  datasets, predecessor model weights, or confirmation records.

Registration SHA-256:
`06de8c3fec296ddf7c9485a21dd1163d68ae241036d8ff1e2b815797d21a55e3`

Handoff ZIP SHA-256:
`390699361e5d21f8953cd820bb655c58b30b21f8a563830c8ab385138f943c68`

## Still unverified

This workspace has neither torch nor transformers installed. No GPU/model
downloads, QLoRA training, real-tokenizer length checks, or learned-model
predictions were run. Token weighting/alignment tests use a fake deterministic
tokenizer. Runtime and zero-truncation checks execute before each GPU training
arm. A successful CPU preflight is not evidence of model improvement.

For handoff, unpack the ZIP into a new empty directory on the Modal volume.
It contains the `edon/experiments/...` hierarchy and can run independently of the
old experiment workspace. This avoids overwriting any old source or artifacts.