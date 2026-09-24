# Program-003 CPU verification

Date: September 8, 2026.

Status: CPU qualification and portable-handoff replay passed. GPU execution,
actual-tokenizer lengths, tensor-loss validation, and model capability remain
unverified locally. No GPU work was launched.

- 29 tests passed in the original workspace.
- Python compileall passed for the new experiment.
- 1,024 training and 128 development native oracle programs passed qualification.
- All 1,152 corresponding traces passed scheduler, transition, derivation,
  and serialization checks.
- Source/config/test/data registration and CPU preflight passed.
- Export: 79 files, 910,531 bytes, no predecessor datasets or confirmation.
- Simulated a Prism export with all JSONL files omitted and final LF stripped
  from text members; restore regenerated the same train/development data and
  reproduced the registration byte-for-byte.
- All 29 tests passed again in that separate restored workspace.
- No confirmation JSONL file existed in either workspace after verification.

Registration SHA-256:
`27356bf7ad608bdc68e5db46deca1cdcaa5d282b0d8a2d2e2579140a4a269c4e`

Handoff ZIP SHA-256:
`3e3e8290a82f4a573cddb920f209c07faf079683d2f7edaa467f741dbcfae812`

The first simulated-restore attempt used an absolute temporary destination,
which the helper correctly rejected. Repeating with the required relative
destination passed. No source code or registration was changed for this test.

The local masking tests use a fake character tokenizer, not the model tokenizer.
They cannot certify the 4,096-token generation or 8,192-token sequence limits.
The runtime preflight checks these against both complete arms before training.
It also checks the chunked loss and its gradients with the installed torch.

These are software and synthetic-target checks, not evidence that either
trained arm will meet development or confirmation gates. The pilot has a single
training seed and explicitly unequal token compute across arms.