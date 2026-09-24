# ACTIONNET-DATA-QUAL-005 Data Design

Each synthetic institution supplies an initial state, a deterministic multi-event queue, and oracle execution under the ordering tuple `(time, priority, sequence, event_id)`. Events after disposition time are deferred.

Pairs cover pivotal, invariant, and contextual interventions. The twelve pivotal mechanisms are preserved from the predecessor semantics, while all generated identities and lineages are new.

DEV-004 repair supervision emphasizes two difficult outputs:

- transitions: post-state, semantic state, decision, and failed conditions;
- queue traces: canonical ordering, execution/defer lists, compact per-step semantics, and final state.

Hashes are intentionally absent from model targets. A downstream deterministic compiler hashes only the state predicted by the model. This removes a token-generation burden without allowing the compiler to infer the correct state.

The validation renderer and families are unseen in training, and the DEV-003 validation set is not reused.