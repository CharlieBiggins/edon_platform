# Program-004 CPU verification

September 10, 2026. CPU-qualified and frozen; no GPU execution or learned result.

- 36 focused tests passed in the project workspace.
- Source-only portable extraction: preflight passed; 35 tests passed and one
  upload-dependent historical replay test skipped, as intended. That replay test
  passed in the original workspace where the hash-bound uploads are present.
- Both Program-003 development scores reproduced exactly from their uploaded
  raw predictions during preparation. Parent trace first-divergence labels:
  10 event-order, 5 state-transition, 6 decision-derivation and 1 event-operand.
  These are observable output differences, not internal-cognition diagnoses.
- Parent train and development reconstructed to their exact registered hashes;
  1,152 source cases supplied structural exclusions. No parent confirmation read.
- 512 ordinary and 512 treatment training records qualified. Exactly 256 case
  IDs are intentionally shared rehearsal across arms. No normalized source
  overlap with known parent exposure; no cross-split family/pair/case/prompt/
  normalized-source overlap in the generated sets.
- 256 fresh development records qualified: 128 ordinary and 128 boundary.
- Oracle-fixture scoring gives 256/256 exact native programs and exact traces.
  Comparing identical oracle-fixture scores correctly holds for no improvement.
  These are synthetic target checks, NOT predictions from a trained model.
- Frozen preflight passed again after portable-handoff verification.
- No successor confirmation file or access record exists. No parent adapter
  weights, model cache, protected material or credentials are in the ZIP.
- Parent source files and Program-003 registration were not edited. Inherited
  files with a stripped terminal LF were accepted only when adding that one LF
  reproduced the original pinned hash; normalized copies are used in the ZIP.

Qualification found dangling actor references in inherited actor-renaming pairs.
The successor excludes complete invalid pairs without modifying the generator.
The ordinary train candidate pool had 170 such pairs across 256 candidate
families; the development ordinary pool had 42 across 64 candidate families.
Counts refer to candidate pools, not released training records. Structural
duplicates are also rejected; boundary sampling has a fixed 64-attempt limit.

## Frozen handoff

Registration:
`sha256:b741af32d0953e76e27273db0518272e8864c8f98899aa1c4bb952ae9f623857`

ZIP:
`sha256:4bb6afe030bb743a090738279f4dc95ee318072f884199a2fd79b62f9da333cd`

93 files, 975,704 bytes. This report is a post-freeze verification artifact and
is not part of the registered implementation or that ZIP.

## Remaining checks

The actual saved parent adapter tree must be verified in Modal. Actual tokenizer
lengths, tensor loss/gradient equivalence, pinned-package continuation behavior,
GPU memory and inference runtime remain external checks. No local torch/model
installation or model download was performed. The package does not claim a
compute-efficiency result, formal statistical power, seed robustness, independent
mechanism transfer, production readiness or mini-IGI completion.