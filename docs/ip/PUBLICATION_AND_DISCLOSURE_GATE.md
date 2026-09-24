# Publication and public-disclosure gate

This gate applies to papers, preprints, public repositories, websites, talks,
demonstrations, pitch materials, videos, customer trials, benchmark releases,
and other external technical disclosures.

## Required reviews

Every proposed release must record:

1. release identifier, owner, scope, and intended publication date;
2. affected invention-family identifiers;
3. prior-public-disclosure inventory status;
4. patent-counsel disposition for each affected family;
5. confirmation that released details are filed, intentionally public, or not
   enabling confidential subject matter;
6. trade-secret review and protected-benchmark review;
7. human-inventorship and assignment review;
8. dependency, model, data, and content-license review;
9. trademark wording and symbol review;
10. scientific claim-registry and evidence review;
11. privacy, security, export, contractual, and partner-approval review when
    applicable.

Any failed or incomplete gate blocks release.

## Language controls

- `patent pending` requires a verified filing receipt and a mapping between the
  disclosed subject matter and the filed application.
- The registered-trademark symbol requires confirmed registration for the mark
  and relevant goods or services. Otherwise use plain text or `TM` after
  clearance guidance.
- `proved`, `validated`, `safe`, `general`, `autonomous`, `production-ready`,
  `IGI`, and similar language must be supported by the scientific claim
  registry; IP status cannot support these words.
- A provisional, patent application, issued patent, trademark filing, or
  copyright registration is not experimental evidence.

## Protected material

Never release:

- active protected evaluation cases or labels;
- custodian credentials or score authorization;
- real-institution raw data without explicit rights and privacy approval;
- confidential thresholds, recipes, prompts, customer mappings, or failure
  libraries designated as trade secrets;
- legal advice, claim drafts, assignments, signatures, or private filing data.

## Improvements after filing

Before disclosing a technical improvement, counsel must determine whether the
earlier application adequately supports it. If not, file an appropriate
follow-on application or deliberately approve public disclosure before release.

## Current repository disposition

The public disclosure inventory is incomplete, no filing receipt is registered,
and all candidate families are marked unfiled. EDON must not currently use
“patent pending” or represent that Bounded IGI has been proved.