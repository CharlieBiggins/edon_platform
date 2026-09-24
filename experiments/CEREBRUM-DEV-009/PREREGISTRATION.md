# CEREBRUM-DEV-009 preregistration

Protocol identity: `CEREBRUM-DEV-009-v1.0.0`  
Frozen: August 16, 2026, after Transfer-007 scoring and before any DEV-009 model run.

## Question

Can fresh-lineage, cross-renderer execution supervision teach the complete
sort--defer--mutate--compare algorithm that failed to transfer reliably in
Transfer-007?

## Registered run

- Condition: `multi_generator_execution_repair`.
- Base: `Qwen/Qwen3-4B-Instruct-2507`.
- Seeds: `26082491`, `26082492`.
- Source: `ACTIONNET-DATA-QUAL-009-result-v1.0.0`.
- Training: 16,128 records; validation: 1,344 fresh records.
- Validation renderer: `DEPENDENCY_GRAPH_PACKET`, unseen in training.
- Context: 4,096 tokens with zero training truncation.
- Epochs: 3; weighted completion loss; resumable training and prediction.

No Transfer-007 case, prompt, prediction, or label may be used for training or
validation. Only the frozen aggregate failure metrics may motivate the design.

## Per-seed advancement gate

Every registered check emitted by `evaluate.py` must pass. The gate includes:

- valid certificates, zero unsafe authorizations, at least 90% decision and
  semantic accuracy, and registered pair-behavior floors;
- at least 90% transition exactness, 95% post-state/decision/failed-condition
  components, and perfect raw schema validity;
- at least 90% queue exactness, 95% order/executed/deferred/final-state
  components, and 90% step-trace exactness;
- at least 85% complete pair exactness, 95% decision-change accuracy, 90%
  certificate decisions, and 90% exact causal and post-state paths;
- zero generation-limit hits.

Both seeds must pass before any new transfer package is created.