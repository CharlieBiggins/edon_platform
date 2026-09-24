# ACTIONNET-DATA-QUAL-008

## Governed multi-domain ActionNet authoring system

This additive package upgrades ActionNet from a single synthetic development corpus into an extensible domain-pack, expert-review, and governance architecture. It does not modify `ACTIONNET-DATA-QUAL-007`, any `CEREBRUM-DEV-007` training artifact, or any protected transfer instrument.

The package currently materializes project-authored synthetic candidates across 24 high-impact sector packs and 20 executable pivotal mechanisms. Two independent schedulers, transition engines, and evaluators must agree before a candidate is admitted. Every candidate remains `training_eligible=false` until the separate source, privacy, expert, adjudication, duplicate, freeze, and release gates pass.

## What is included

- Domain registry covering health, finance, government, justice, infrastructure, industry, environment, social systems, technology, public safety, science, and food systems.
- Twenty executable pivotal mechanisms, including consent withdrawal, quorum failure, custody breaks, conditional delegation, reporting deadlines, budget encumbrance, quality holds, and recall incompletion.
- Four structured tasks: certificate, transition, queue trace, and paired contrast.
- Deterministic expert routing based on verified domain, specialty, jurisdiction, credential validity, calibration, tenant permission, and conflicts.
- JSON contracts for governed app feedback, expert profiles, expert reviews, ActionNet candidates, and training eligibility.
- Explicit author/reviewer/adjudicator separation for high-risk cases.
- Frozen public and protected family reservations that are not materialized.

## Status meaning

`READY_FOR_EXPERT_DOMAIN_AUTHORING` means the synthetic authoring framework is internally consistent and ready to receive properly sourced expert work. It does **not** mean:

- the domain packs are complete descriptions of their industries;
- a licensed or authorized expert has validated them;
- customer or real-institution data is present;
- any record is approved for Cerebrum training;
- Cerebrum or ActionNet is binding authority;
- the package is safe for production decision making.

## Run

```bash
python run_campaign.py
python -m unittest discover -s tests -v
```

The Kernel remains the binding authority in the EDON architecture. ActionNet cases and Cerebrum outputs are non-authoritative evidence and proposals.