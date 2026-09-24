# Intellectual-property documentation

Status: `PROCESS_DOCUMENTATION_ONLY_NOT_A_FILING`

This directory organizes EDON's patent, trade-secret, trademark, copyright,
contract, data-rights, and publication-control work. It is designed for an
attorney handoff while preserving the repository's scientific claim boundaries.
It is not legal advice and does not establish novelty, patentability, freedom to
operate, ownership, registration, or a pending patent application.

## Core principle

```text
Patents       protect enabled technical mechanisms selected for disclosure
Trade secrets protect valuable confidential implementation knowledge
Trademarks    identify EDON's commercial source after clearance
Copyright     protects original expression, not the underlying method
Contracts     establish ownership, confidentiality, data rights, and permitted use
```

Scientific proof is separate. EDON must not describe an application, patent,
or governance document as proof that bounded IGI has been achieved.

## File index

| File | Purpose |
| --- | --- |
| `IP_STRATEGY.md` | Layered protection strategy and decision rules |
| `INVENTION_FAMILIES.md` | Sanitized candidate families and technical boundaries |
| `PATENT_DISCLOSURE_GUIDE.md` | Requirements for an enabling counsel-ready disclosure |
| `PRIOR_ART_AND_ELIGIBILITY_PLAN.md` | Search, eligibility, novelty, and freedom-to-operate workflow |
| `PUBLICATION_AND_DISCLOSURE_GATE.md` | Filing-before-release and scientific-claim controls |
| `TRADE_SECRET_PROGRAM.md` | Confidentiality classification and reasonable-control program |
| `TRADEMARK_AND_BRAND_PLAN.md` | Clearance-first brand architecture and symbol rules |
| `COPYRIGHT_CONTRACTS_AND_DATA_RIGHTS.md` | Ownership, assignments, licenses, data, and dependency controls |
| `COUNSEL_HANDOFF.md` | Attorney package and first-90-day execution plan |
| `templates/` | Sanitized forms; completed confidential versions remain outside Git |

Machine-readable public status lives under [`governance/ip/`](../../governance/ip/README.md).

## Public/private boundary

The repository may contain:

- candidate family names and non-confidential summaries;
- links to already-versioned architecture and source files;
- filing status, filing date, public application number, and receipt hash after
  counsel approves publication;
- public-disclosure metadata;
- brand clearance and registration status;
- policy and release-review templates.

The repository must not contain:

- attorney-client communications or legal opinions;
- unpublished claim drafts or confidential invention disclosures;
- actual trade-secret values, recipes, thresholds, prompts, customer knowledge,
  or protected evaluation contents;
- signed assignments, personal addresses, signatures, payment data, or account
  credentials;
- statements that an unfiled family is patent pending or patentable.

## Validation

```bash
python scripts/release/validate_ip_governance.py
```

The validator checks structure and status consistency. It cannot determine
patentability, inventorship, ownership, secrecy, or legal sufficiency.