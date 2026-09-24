# CEREBRUM-LATENT-COORD-001

This package reserves EDON's first prospective evaluation of whether Cerebrum
can detect and reason about coordination encoded in institutional state rather
than only explicit agent communication.

Current status:

`SHELL_READY_INSTRUMENT_AND_CANDIDATE_UNMATERIALIZED`

The intended capability is:

```text
detect -> attribute -> reconstruct -> predict -> govern
```

The shell freezes the representation, conditions, task allocation, causal
controls, metrics, safety boundary, custody rules, and claim language. It does
not contain cases, labels, a generator, oracle, scorer, trained candidate,
predictions, or a result.

## Required development sequence

1. Create a new ActionNet data identity for project-authored development cases.
2. Train or configure a candidate without access to the protected instrument.
3. Freeze candidate model, prompt, parser, and state-projector hashes.
4. Have an independent custodian construct the reserved instrument and causal
   oracle.
5. Freeze label-free predictions from every registered condition.
6. Perform one protected score transaction.

Development cases cannot establish the protected claim. Exposed cases and
labels cannot be reused for repair under this identity.

## Shell validation

```bash
cd experiments/CEREBRUM-LATENT-COORD-001
python preflight.py
python -m unittest discover -s tests -v
```

Passing preflight is protocol infrastructure only.