# CEREBRUM-DEV-004 Handoff

Use `ACTIONNET-DATA-QUAL-005-result-v1.0.0` only under the separate `CEREBRUM-DEV-004` identity.

Required downstream controls:

1. Preserve ActionNet-005 file hashes in the prepared-data manifest.
2. Train only the preregistered `structured_repair` condition.
3. Keep training and inference context limits identical.
4. Abort rather than silently truncate a training example.
5. Verify generation limits against tokenized training completions.
6. Record generation-limit hits during prediction.
7. Derive hashes only from model-predicted states.
8. Evaluate only on fresh families 90--93 and `AUDIT_PACKET`.
9. Never materialize or tune on future-public or protected families.
10. Keep `binding_authority=false` throughout.

The handoff is resource-contingent. Preparation and transparent-rule verification are CPU-safe; learned-model execution requires a compatible GPU and available compute budget.