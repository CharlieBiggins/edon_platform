# EDON trade-secret program

## Purpose

Preserve commercially valuable confidential information through documented,
reasonable controls. Merely calling material confidential is insufficient as an
operating practice. This public document describes categories and controls; it
must never contain the secret values themselves.

## Candidate categories

| Category | Examples of potentially protected material |
| --- | --- |
| ActionNet corpus | non-public trajectories, expert corrections, counterfactuals, failure libraries, customer-derived experience |
| Generation system | prompts, templates, generator mixtures, mutation rules, rejection thresholds, hard-negative construction |
| Training recipe | mixtures, curricula, weighting, reward functions, schedules, selection and checkpoint methods |
| Cerebrum runtime | routing, context assembly, retrieval, memory compression, confidence and abstention policies, production optimizations |
| Protected evaluation | unseen institutions, attack corpora, holdouts, scoring secrets, custodian-only cases |
| Customer operations | onboarding mappings, integrations, deployment patterns, pricing, non-public customer knowledge |
| Commercial strategy | roadmaps, bids, forecasts, partner terms, acquisition strategy |

## Required controls

- named owner and custodian for every secret category;
- explicit business value and secrecy rationale;
- need-to-know role-based access with MFA;
- encrypted approved storage and transport;
- access logging and periodic entitlement review;
- confidentiality and invention-assignment coverage;
- clear confidential markings and handling instructions;
- restrictions on local copies, personal accounts, public AI services, and
  removable media;
- controlled disclosure under appropriate agreements;
- incident response, access revocation, and offboarding confirmation;
- retention, deletion, and downgrade rules;
- periodic verification that the information is still non-public and valuable.

## Repository rule

The Git-facing repository stores only category identifiers, owners by role,
status, and approved hashes. It does not store:

- the secret itself;
- a reversible summary;
- a file path that exposes private infrastructure;
- personal data or signatures;
- counsel communications.

The provided trade-secret template must be completed in the private system.

## Patent boundary review

Before filing, identify every secret that would be disclosed by the proposed
application. Record one decision:

- disclose intentionally for patent coverage;
- redact because it is unnecessary to enable the selected invention;
- keep as a separate secret implementation optimization;
- defer the filing pending a better portfolio decision.

After public disclosure, the disclosed information must not remain classified
as an EDON trade secret.

## Scientific custody

Protected benchmarks are governed both as confidential assets and as scientific
instruments. Model developers must not receive protected labels or case-specific
feedback before prediction freeze. An independent custodian may permit
evaluation without transferring the benchmark into EDON's training environment.