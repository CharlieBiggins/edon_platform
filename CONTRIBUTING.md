# Contributing

## Principles

1. Preserve frozen results; repairs receive new protocol identities.
2. Separate development, public, protected, and real-institution evidence.
3. Keep labels and answer-defining fields outside prediction runtimes.
4. Preserve conflicts among normative, operational, and behavioral sources.
5. Never grant a learned model binding institutional authority.
6. Do not publish enabling invention details or protected commercial knowledge
   without the IP/public-disclosure gate.

## Required changes

Every experiment contribution must include `README.md`, `PROTOCOL.md`,
`CLAIMS.md`, `manifest.json`, deterministic tests, and a frozen gate.

Schema changes require:

- a version increment;
- migration notes;
- backward-compatibility tests or an explicit breaking-change declaration;
- provenance and claim-registry review.

## Pull-request checklist

- [ ] Tests pass with `python -m unittest discover -s tests -v`.
- [ ] `PYTHONPATH=src python -m edon.cli validate .` passes.
- [ ] No secrets, raw protected data, model weights, or checkpoints are included.
- [ ] No confidential invention disclosure, legal advice, assignment, signature,
      trade-secret value, or unreviewed protected benchmark is included.
- [ ] Affected candidate invention families and prior disclosures have been
      reviewed for public releases.
- [ ] Patent, trademark, ownership, and scientific-status language matches the
      machine-readable governance records.
- [ ] Claims are narrower than or equal to the attached evidence.
- [ ] New failures and negative results are retained.