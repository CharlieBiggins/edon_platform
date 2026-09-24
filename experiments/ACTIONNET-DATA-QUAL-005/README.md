# ACTIONNET-DATA-QUAL-005

Frozen result identity: `ACTIONNET-DATA-QUAL-005-result-v1.0.0`.

This package generates the fresh-lineage synthetic dataset for `CEREBRUM-DEV-004`. It retains the independently cross-checked EventNet scheduler and transition semantics while changing case identifiers, generator/source/institution/graph lineages, semantic families, domains, and the held-out renderer.

The generated package contains:

- 5,040 training records across certificate, transition, queue-trace, and pair-contrast tasks;
- 420 fresh validation records;
- training families 70--81 and validation families 90--93;
- training renderers `FORMAL`, `EVENT_STREAM`, and `CASE_DOCKET`;
- the held-out validation renderer `AUDIT_PACKET`;
- compact transition and queue targets that exclude cryptographic hashes;
- reserved, unmaterialized future-public families 94--97 and protected families 98--101.

Generate and verify with:

```bash
python run_campaign.py
python -m unittest discover -s tests -v
```

This result qualifies only an internal synthetic repair corpus. It does not establish source grounding, public performance, real-institution validity, autonomous authority, or production readiness.