# CEREBRUM-DEV-006 handoff

Authorized input: `dataset/train.jsonl`.  
Internal fresh validation: `dataset/repair_validation.jsonl`.  
Registered condition: `appeal_certificate_repair`.  
Registered seeds: `26081461`, `26081462`.

DEV-004 artifacts and validation cases must remain excluded from training.
Both DEV-006 seeds must independently pass the complete gate before any new
independent-transfer successor is constructed or executed.