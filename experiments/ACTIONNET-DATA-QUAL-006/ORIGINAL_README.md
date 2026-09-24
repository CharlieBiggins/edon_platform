# ACTIONNET-DATA-QUAL-006

This additive successor responds to the frozen CEREBRUM-DEV-004 seed-2 result.
Seed 26081242 passed 16/17 gates but classified all three held-renderer resolved
appeal certificates as `CONTESTED` instead of `ALLOW`. DEV-004 and its exposed
validation cases remain immutable.

The package generates 8,064 fresh-lineage training records and 1,344 new
repair-validation records. It retains the registered EventNet semantics while
increasing resolved/unresolved appeal coverage, varying appeal timing, adding
matched `ALLOW`/`CONTESTED` hard negatives, and using three new training
renderers plus a held-out `REVIEW_MEMORANDUM` renderer.

```bash
python run_campaign.py
python -m unittest discover -s tests -v
sha256sum -c results/checksums.sha256
```

This is project-authored synthetic development data. It is not public,
protected, real-institution, autonomous-authority, or production evidence.