# ACTIONNET-DATA-QUAL-012

Fresh synthetic calibration data for the single DEV-011 near-miss: two
resolved appeals were conservatively classified as `CONTESTED` while all
unresolved appeals were safely classified.

The package contains 384 balanced, symmetrically weighted training certificates
and 64 held-renderer validation certificates under new semantic families,
cases, renderers, and lineages.

```bash
python run_campaign.py
python -m pytest -q
```

This is adaptive development data, not full regression or transfer evidence.