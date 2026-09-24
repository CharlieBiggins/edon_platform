# CEREBRUM-DEV-007 handoff

Use `dataset/train.jsonl` only for the registered
`cross_renderer_execution_repair` condition. Use
`dataset/repair_validation.jsonl` only for fresh internal validation.

Preserve sample weights and compact targets. Do not put lineage metadata,
compiler inputs, hashes, or hidden reasoning into model prompts. Training and
inference contexts must be 4,096 tokens with zero training truncation. The
Transfer-006 instrument remains frozen and is not a DEV-007 training source.