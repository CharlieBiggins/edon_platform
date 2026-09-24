# Protocol

- Source: `ACTIONNET-DATA-QUAL-007`.
- Condition: `cross_renderer_execution_repair`.
- Training records: 16,128; validation records: 1,344.
- Seeds: 26081671 and 26081672.
- Base: `Qwen/Qwen3-4B-Instruct-2507`.
- Context: matched 4,096-token training/inference limit with zero truncation.
- Advancement: every seed must pass all 27 exactness, safety, renderer, and
  generation checks; both registered seeds must pass the frozen summary.