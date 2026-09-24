# ACTIONNET-DATA-QUAL-013

Fresh synthetic near-clock appeal data following the DEV-012 learning-curve
audit. Every pivotal pair differs only between a `clock-1` executed resolution
and a `clock+1` deferred resolution.

The package contains 192 training certificates, 32 development-selection
certificates, and 64 untouched confirmation certificates. The three splits use
disjoint semantic families, pairs, cases, and renderers.

```bash
python run_campaign.py
python -m pytest -q
```

Development selection is explicitly adaptive. Confirmation remains single-use.
This package is not full-regression or transfer evidence.
