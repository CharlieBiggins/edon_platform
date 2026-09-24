# Protocol

- Source: ACTIONNET-DATA-QUAL-005.
- Condition: `structured_repair`, 5,040 records.
- Seeds: 26081241 and 26081242.
- Context: matched 2,048-token training/inference limit with zero truncation.
- Tasks: certificates, transitions, queue traces, and pair contrasts.
- Compiler: hashes and changed fields derive only from model-predicted states.
- Advancement: each seed must pass 17/17 checks; both seeds must pass the frozen
  two-seed reproducibility summary.