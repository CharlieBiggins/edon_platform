# IP governance records

Status: `PUBLIC_SANITIZED_REGISTRY_COUNSEL_REVIEW_REQUIRED`

This directory contains the machine-readable public layer of EDON's
intellectual-property governance. It records process status and sanitized
candidate categories only. It is not a patent filing, legal opinion, trademark
clearance, ownership determination, or trade-secret vault.

## Records

| File | Purpose |
| --- | --- |
| `policy.json` | Repository-wide IP and release rules |
| `candidate-families.json` | Sanitized candidate invention-family status |
| `disclosure-register.json` | Public-disclosure inventory status and approved entries |
| `trademark-register.json` | Clearance and registration status; no availability conclusions |
| `trade-secret-categories.json` | Category-level controls without secret values |
| `rights-register.json` | Contributor, dependency, model, data, and customer-rights audit status |
| `release-review.template.json` | Fail-closed record for a proposed public release |
| `schemas/` | Structural contracts for the records |

## Confidentiality boundary

Completed invention disclosures, prior-art legal analysis, claim drafts,
attorney communications, assignments, signatures, personal data, filing
credentials, trade-secret values, customer information, and protected benchmark
contents must remain outside Git. Counsel may authorize a sanitized filing
number, date, status, and receipt hash for later publication.

## Validation

```bash
python scripts/release/validate_ip_governance.py
```

A passing validation means only that the public records are structurally
consistent and appropriately cautious.