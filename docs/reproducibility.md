# Reproducibility

## Required experiment record

Every major result must preserve:

- protocol and preregistration identity;
- source, dataset, model, adapter, config, and scorer hashes;
- seeds and software/hardware environment;
- label-free prediction inputs and prediction hashes;
- custodian-only labels and scoring authorization;
- raw and aggregate results;
- claim boundary and known failures.

## Reproduction levels

1. **Structural:** files, schemas, and manifests validate.
2. **Deterministic:** generators and scorers reproduce byte-identical outputs.
3. **Computational:** independent execution reproduces registered metrics.
4. **Scientific:** independent authorship, cases, custody, and analysis reproduce
   the conclusion.

Levels 1–3 do not automatically imply level 4.

## Local checks

```bash
PYTHONPATH=src python -m edon.cli validate .
python -m unittest discover -s tests -v
```