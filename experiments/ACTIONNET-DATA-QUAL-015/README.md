# ACTIONNET-DATA-QUAL-015

Mixed-retention repair data after the DEV-014 full-regression hold. Training
contains 384 deterministic replay records: 352 multi-task records from the
qualified DEV-010 training split and 32 near-clock appeal certificates from
the qualified DEV-013 training split. Transition and queue-trace supervision
are deliberately emphasized.

Fresh data consists of a 64-case four-task development-selection split and a
single-use 192-case four-task confirmation split. DEV-014 validation cases are
excluded and prohibited from training.

```bash
python run_campaign.py
```