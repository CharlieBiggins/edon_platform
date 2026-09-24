# Product security boundary

- Raw institutional data should remain inside the customer-controlled plane.
- Only governed abstractions may be considered for reusable ActionNet records.
- The governed intake API rejects fields associated with raw payloads, direct
  identifiers, credentials, account identifiers, and biometric records. This
  is a defense-in-depth control, not a substitute for local DLP or privacy review.
- Protected experiences require an `ACTIONNET_CUSTODIAN` or `ADMIN` identity.
- Protected records cannot enter training, development, or diagnostic exposure.
- Training eligibility requires domain, safety, lineage, and training approvals;
  real governed abstractions also require privacy approval.
- Domain and safety approvals require distinct reviewers.
- Every product record is immutable and every mutation request creates a
  tenant-specific SHA-256 audit-chain event.
- Intervention and acquisition outputs are candidates. They cannot contain
  execution authority and cannot bypass a Kernel.
- Composition, counterfactual, and human-behavior outputs are synthetic product
  artifacts. None receives binding authority or automatic training eligibility.
- Global ActionNet promotion accepts only normalized abstractions and rejects
  tenant IDs, local experience IDs, raw payloads, direct identifiers,
  credentials, and authority-bearing fields.
- A global release revalidates the current local eligibility state. Subsequent
  local quarantine blocks release.
- Memory, ActionNet releases, C1 version records, and model dispositions never
  authorize automatic or online weight updates.

The internal bearer-token implementation is not sufficient for production.
Deploy behind TLS, OIDC/workload identity, a secret manager, network policy,
rate limiting, structured audit export, and environment-specific threat models.