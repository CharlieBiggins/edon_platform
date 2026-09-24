# ACTIONNET-DATA-QUAL-007

Fresh-lineage synthetic data qualification for the CEREBRUM-DEV-007
execution-transfer repair. The corpus was created after the August 16, 2026
Transfer-006 score and does not reuse any Transfer-006 case, prompt, prediction,
or label.

The repair targets the observed algorithmic failures: canonical queue order,
decision-clock deferral, exact post-state mutation, compact step traces, and
pairwise causal/post-state diffs. Every trajectory contains both executed and
deferred events, clocks vary from 8 through 12, and every final state changes on
at least two paths.

Run:

```bash
python -m unittest discover -s tests -v
python run_campaign.py
```

The qualified result is `ACTIONNET-DATA-QUAL-007-result-v1.0.0`. It is internal,
synthetic, non-authoritative, and not confirmatory or production evidence.