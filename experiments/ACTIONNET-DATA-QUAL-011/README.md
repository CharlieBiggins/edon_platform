# ACTIONNET-DATA-QUAL-011

Fresh synthetic data for one observed DEV-010 failure boundary only:
`UNRESOLVED_APPEAL` certificate disposition. The corpus contains paired resolved
(`ALLOW`) and unresolved-at-the-clock (`CONTESTED`) trajectories under new
semantic families and new renderers.

Run:

```bash
python run_campaign.py
python -m pytest -q
```

Registered output: 768 focused training records and 64 held-renderer validation
records. This package does not test queue, transition, pair-contrast, general
regression, transfer, or real-institution behavior.