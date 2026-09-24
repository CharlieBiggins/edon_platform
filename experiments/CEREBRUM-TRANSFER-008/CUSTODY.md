# Custody and role separation

## Candidate team

May supply frozen adapter bytes, hashes, model revision, inference dependencies,
and the label-independent runtime interface. It may not inspect protected cases
or labels before prediction freeze.

## Instrument team

Independently implements the generator, semantics, and oracle. It receives the
frozen interface and prohibited-lineage registry, not candidate predictions or
development failures.

Before instrument materialization, it must also freeze the exact base-model
revision, the model-agnostic schema constraint, the zero-retry policy, and the
public non-protected interface prompt pack used by the matched baselines. The
prompt pack may teach syntax only and cannot contain instrument-derived or
answer-bearing material.

## Custodian

Holds the instrument seed, source bytes, label file, case order, overlap audit,
candidate registry, learned baseline registry, baseline contract, prompt-pack
hash, and score authorization. It publishes only commitments before prediction
freeze and performs or witnesses the single score transaction.

## Statistical reviewer

Verifies denominators, gates, raw and interface-matched base comparisons,
strongest-baseline selection, conditional-on-valid and compiled metrics,
missing-data treatment, and disposition. It cannot authorize a second score
because the first result is unfavorable.

No protected case or label may be committed to this public shell.