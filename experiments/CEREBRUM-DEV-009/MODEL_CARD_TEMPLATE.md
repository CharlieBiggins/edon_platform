# CEREBRUM-DEV-009 model card template

- Base model: `Qwen/Qwen3-4B-Instruct-2507`
- Condition: `multi_generator_execution_repair`
- Seed: `26082491` or `26082492`
- Training source: `ACTIONNET-DATA-QUAL-009-result-v1.0.0`
- Training records: 16,128
- Validation records: 1,344
- Transfer-007 cases reused: no

Record package versions, GPU, adapter hash, training manifest, resume history,
all advancement checks, output-limit hits, and exact transition/queue/pair
component metrics. State clearly that the adapter is synthetic,
non-authoritative, and not production validated.