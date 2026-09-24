# Protocol

## Lifecycle

```text
reserved shell
  -> RB1 two-seed score passes
  -> candidate adapter hashes frozen
  -> independent custodian commitment recorded
  -> materialization authorization
  -> label-free runtime freeze
  -> base and two adapters predict
  -> three prediction manifests freeze
  -> one custodied score transaction
  -> immutable disposition
```

No stage may be skipped. Candidate failure leaves the reservation
unmaterialized.

## Compute boundary

All conditions use deterministic decoding, the same base-model revision,
inference context, task token limits, compiler contract, hardware class, and
case order. Prediction is resumable per case. Predictions are hashed before the
custodian opens labels.

## Runtime firewall

The prediction runtime may contain only model loading, adapter loading,
tokenization, deterministic generation, raw-schema parsing, deterministic
compilation, checkpointing, and manifest generation. It may not contain labels,
targets, oracle state, scoring thresholds, training paths, protected overlap
references, or post-hoc correction rules.

## Scoring lock

Scoring is unavailable until base and both RB1 candidate prediction files and
manifests are complete and hash-frozen. The scorer must reject partial coverage,
duplicate IDs, extra IDs, mismatched instrument hashes, changed candidate
hashes, or more than one score authorization.

## Exposure rule

Once any Transfer-008 case, prompt, output, or label is exposed, it is forever
prohibited from successor training, prompt tuning, model selection, threshold
tuning, or confirmatory reuse.