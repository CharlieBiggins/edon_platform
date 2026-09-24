# ACTIONNET-DATA-QUAL-016

Fresh narrow-repair data after the DEV-015 development hold. Training contains
368 project-authored synthetic records with 16 delayed-evidence pivotal pairs,
balanced ALLOW/ABSTAIN certificates, and broad exact-state reconstruction
coverage. It includes 96 transitions, 96 queue traces, 48 pair contrasts, 64
certificates, 32 queue-order records, and 32 queue-partition records.

Fresh data also contains a 64-case four-task development-selection split and a
single-use 192-case full confirmation. No DEV-014 or DEV-015 validation case is
used for training.

```bash
python run_campaign.py
```