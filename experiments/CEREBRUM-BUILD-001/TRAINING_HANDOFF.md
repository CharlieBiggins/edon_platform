# Training handoff

No training corpus or adapter is bundled inside Build-001. The additive
`CEREBRUM-CLOSED-LOOP-DEV-001` package now provides the development-only
interactive curriculum and an authorized training-release manifest. Before GPU
execution, verify that release and register a model-specific training manifest
containing:

- release identifier and creation date;
- canonical JSONL file paths and SHA-256 hashes;
- source experiment and generator lineage;
- task, domain, mechanism, renderer, and pair-class counts;
- protected-overlap exclusions;
- source rights and privacy disposition;
- explicit confirmation that every included row is training eligible;
- chosen base-model revision and tokenizer revision;
- registered exploratory seed and QLoRA configuration.

The existing DEV-009 QLoRA code may be reused as engineering infrastructure,
but Build-001 must write to a new artifact directory and emit a Build-001 model
manifest. It must not overwrite an RB1 adapter, prediction, freeze, or result.
Training must consume only the closed-loop package's training split; its
validation oracle remains unavailable to the training runtime.

After training, record:

```text
models/cerebrum-build-001/<version>/
  model-manifest.json
  final-adapter/
  training-manifest.json
  checksums.sha256
```

Large weights remain outside Git. The manifest and checksums may be registered
in the repository after the artifact is frozen.