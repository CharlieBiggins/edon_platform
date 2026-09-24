# Platform 002 active-experience architecture

```text
Canonical Institutional IR
  objects + references + time + epistemic state + behavior assumptions
                         |
                         v
Atlas mechanisms -> executable Composition Engine
                         |
                         v
              horizon-bearing trajectory
                         |
            +------------+-------------+
            |                          |
            v                          v
   Experience Ledger          Counterfactual Engine
                                       |
                                       v
                            replay-verified children

Customer-controlled plane
  source event -> local minimization -> governed abstraction attestation
                                       |
                                       v
                               governed intake
                                       |
                                       v
                              privacy/review gates
```

## Canonical rules

- Every IR object has an immutable identity, explicit type, tuple component,
  attributes, closed references, temporal state, and epistemic state.
- Actor behavior is optional and assumption-driven. It is never represented as
  observed human ground truth without separate evidence and review.
- Compositions use registered mechanisms and registered edges only.
- `CAUSES` and `PRECONDITION_FOR` determine causal order; cycles fail closed.
- `AMPLIFIES`, `MITIGATES`, and `INHIBITS` have bounded deterministic semantics.
- Counterfactual branches must replay before they can enter custody.
- Unknown critical evidence produces `ABSTAIN_ACQUIRE_EVIDENCE`.
- Raw customer records are outside this product boundary. Intake accepts a
  locally minimized abstraction plus rights and redaction attestations.
- Every output is non-authoritative and has `binding_authority=false`.

## Product versus scientific claims

Platform 002 demonstrates that these workflows execute and preserve their
governance contracts. Whether its IR improves learned transfer, its simulations
represent real institutions, or its counterfactuals are causally valid remains
a separate research and external-validation question.