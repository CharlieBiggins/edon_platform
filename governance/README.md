# Governance

Governance connects scientific claims, risks, review protocols, and release
decisions. It does not grant institutional authority by itself.

## Architecture governance

[`architecture/`](architecture/README.md) records additive terminology and
architecture decisions without rewriting historical experiments. The frozen
`CEREBRUM-PLATFORM-VISION-002` defines the controlling successor platform
architecture while Vision-001 remains frozen. Both explicitly preserve their
not-implemented claim boundary.
`CEREBRUM-MATURE-PLATFORM-SPEC-001` freezes the corresponding mature product
and technical-contract map without altering either vision or creating a
capability claim.

## Bounded institutional-intelligence scopes

[`igi-scope/`](igi-scope/README.md) contains frozen definitions of the
institutional environment classes over which future bounded generality claims
may be evaluated. `EDON-IGI-SCOPE-001` defines the first finite environment
class, three evaluation profiles, safety invariants, exclusions, and evidence
tiers. It is a scope definition, not an IGI result.

## Intellectual-property and disclosure governance

[`ip/`](ip/README.md) contains sanitized machine-readable records for candidate
invention families, public disclosures, brand status, trade-secret categories,
rights audits, and fail-closed release review. Confidential disclosures, legal
advice, assignments, signatures, secret values, and protected evaluations do
not belong in this repository.

The IP records do not determine patentability, inventorship, ownership,
trademark availability, freedom to operate, or scientific validity. Run:

```bash
python scripts/release/validate_ip_governance.py
```