# ACTIONNET-DATA-QUAL-002

This package is an additive observability repair for the development corpus. It never overwrites the original ACTIONNET-DATA-QUAL-001 result.

Run:

```bash
python run_campaign.py
python -m unittest discover -s tests -v
```

Use this corpus, rather than v1, for `CEREBRUM-DEV-001`. The repair makes event values visible in memo observations, represents malformed typed input observably, and removes case/institution identifiers from the model-facing `input` object.

The result is internal synthetic development data only. The generator, renderer repair, engines, cases, and oracle remain under shared project authorship.