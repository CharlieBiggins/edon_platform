# ACTIONNET-DATA-QUAL-001

Standalone ActionNet development-data qualification campaign.

The package generates semantic-first institutional trajectories, verifies every transition and outcome with two separately implemented engines, creates minimal counterfactual pairs, audits invariances, renders multiple observation views, separates model inputs from oracle records, constructs lineage-isolated splits, checks leakage and duplicates, and freezes a checksummed dataset release.

Run:

```bash
python run_campaign.py
python -m unittest discover -s tests -v
```

A passing result authorizes only development LoRA pipeline work. It is not a protected, source-grounded, design-partner, or confirmatory dataset.