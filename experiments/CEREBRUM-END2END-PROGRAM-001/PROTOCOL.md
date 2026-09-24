# Protocol

1. Bind the completed DEV-020 result, error audit, and frozen interface spec.
2. Start a new adapter from the base Qwen revision; import no earlier adapter.
3. Freeze the untrained base as step 0 on development before any training
   artifact is created.
4. Train for two complete registered passes over 1,024 native program targets.
5. Freeze predictions for steps 64 and 128 on the same development cases.
6. Select at most one checkpoint using absolute and paired-improvement gates,
   including an exact one-sided McNemar test for program correctness.
7. Open 256 confirmation trajectories once only if a checkpoint qualifies,
   then evaluate both the selected checkpoint and the unchanged base.
8. Parse and execute every generated program with two independent engines.
9. Report model-alone safety separately from deterministic-envelope coverage.