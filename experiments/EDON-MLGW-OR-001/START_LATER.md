# Start later checklist

Do not interrupt active CEREBRUM-DEV-009-RB1 execution for this program.

When the transfer work is complete:

```bash
cd edon/experiments/EDON-MLGW-OR-001
python preflight.py
python -m unittest discover -s tests -v
python freeze_timeline.py
```

Then complete these external prerequisites before any protected simulation:

1. Obtain MLGW authorization and appoint an independent custodian.
2. Freeze the data dictionary, source bytes, permissions, and retention plan.
3. Import internal data only in the approved protected environment.
4. Run the ten partner-data readiness gates in `DATA_ACQUISITION.md`.
5. Commission an independently engineered simulator and conventional OR
   comparator.
6. Select development and protected storms before candidate tuning.
7. Freeze controller runtimes, budgets, safety validators, uncertainty model,
   seeds, and scoring.
8. Execute protected historical replay once.
9. Advance to prospective shadow mode only if the registered threshold passes.

The current public ledger may be extended using `capture_record.py`, but new
records remain non-authoritative until the cited source bytes are archived and
hashed.