# CEREBRUM-DEV-009 GPU handoff

This package is the additive, non-authoritative multi-generator repair campaign
created after the `CEREBRUM-TRANSFER-007-STAGED-DIAGNOSTIC` smoke gate failed on
August 24, 2026. It trains on the fresh ActionNet-009 `LEDGER` and `MATRIX`
profiles and validates on the held-out `GRAPH` profile. No Transfer-007 case,
prompt, prediction, or label is reused.

Run the CPU-safe checks first:

```bash
python prepare_data.py
python -m unittest discover -s tests -v
python preflight.py
```

The expected preflight result is `33/33` controls with status
`READY_FOR_RESOURCE_CONTINGENT_EXECUTION`.

On a Lightning GPU studio, inspect the hardware and start the registered runs:

```bash
python lightning_launcher.py probe
python lightning_launcher.py smoke --condition multi_generator_execution_repair --seed 26082491
python lightning_launcher.py train --condition multi_generator_execution_repair --seed 26082491
python lightning_launcher.py train --condition multi_generator_execution_repair --seed 26082492
```

The model remains non-authoritative. Passing this internal synthetic campaign
does not establish real-institution transfer or authorize binding execution.