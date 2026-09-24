# Protocol

- Source: `ACTIONNET-DATA-QUAL-006`.
- Primary condition: `appeal_certificate_repair`.
- Training records: 8,064.
- Fresh validation records: 1,344.
- Seeds: 26081461 and 26081462.
- Base model: `Qwen/Qwen3-4B-Instruct-2507`.
- Context: matched 2,048-token training/inference limit with zero truncation.
- Tasks: certificates, transitions, queue traces, and pair contrasts.
- Explicit appeal checks: unresolved-appeal certificate accuracy, resolved
  appeal `ALLOW`, and unresolved appeal `CONTESTED`, each at least 0.90.
- Advancement: each seed must pass 20/20 checks and both registered seeds must
  pass the frozen summary.