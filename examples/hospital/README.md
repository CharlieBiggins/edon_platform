# Synthetic hospital example

Demonstrates a high-risk candidate mechanism. Human review remains mandatory even
at high extraction confidence. This is not clinical guidance or a validated EHR
integration.

Run the compiler example from the repository root:

```bash
PYTHONPATH=src python -m edon.cli compile-institution \
  examples/hospital/compiler-input.json \
  --output examples/hospital/compiler-output.json
```

The synthetic sources intentionally disagree about medication-release authority
and timing. The compiler must retain those disagreements and route that mechanism
for domain and safety review. The low-risk inventory-audit fact agrees across all
three layers and should not enter the focused exception queue.