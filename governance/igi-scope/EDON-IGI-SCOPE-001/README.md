# EDON-IGI-SCOPE-001

Frozen: 2026-08-25  
Status: `FROZEN_DEFINITION_NO_IGI_RESULT`

`EDON-IGI-SCOPE-001` defines the first explicit universe of institutional
environments over which EDON may eventually evaluate bounded general
institutional intelligence.

This package does not assert that Cerebrum covers the universe. It defines the
universe, its profiles, its exclusions, the required safety invariants, and the
evidence tiers needed before progressively stronger claims are permitted.

## Entry points

- [`SCOPE.md`](SCOPE.md): formal environment and claim definition;
- [`EVALUATION_PROFILES.md`](EVALUATION_PROFILES.md): concrete size and compute profiles;
- [`CLAIMS.md`](CLAIMS.md): current and prohibited language;
- [`VERSIONING.md`](VERSIONING.md): immutable scope-version policy;
- [`scope.json`](scope.json): machine-readable scope;
- [`coverage-matrix.json`](coverage-matrix.json): current evidence coverage;
- [`scope-manifest.json`](scope-manifest.json): content-bound scope identity;
- [`inventory.json`](inventory.json): package file hashes.

## Relationship to current work

- RB1 is a same-program, two-seed prerequisite experiment outside this scope
  package.
- Transfer-008 is reserved as the first narrow independent EventNet evidence
  slice. It cannot cover planning, tools, federation, long-horizon learning, or
  real-institution validity.
- Build-001 is an exploratory engineering lane. Its development benchmarks are
  not protected evidence for Scope-001.

## Validate

```bash
cd edon/governance/igi-scope/EDON-IGI-SCOPE-001
python preflight.py
python -m unittest discover -s tests -v
```