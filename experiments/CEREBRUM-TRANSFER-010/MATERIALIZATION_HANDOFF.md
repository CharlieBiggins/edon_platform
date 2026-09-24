# Independent materialization handoff

Do not construct the protected instrument from this repository.

After both DEV-010 candidates and all baselines are frozen, provide the
independent team with:

- reservation.json;
- config/transfer-gates.json;
- config/baseline-contract.json;
- config/authorship-custody-contract.json;
- schemas/protected-input.schema.json;
- schemas/protected-prediction.schema.json; and
- lineage/prohibited-predecessors.json.

The independent team returns only hash commitments before authorization.
Protected inputs, labels, generator, oracle, runtime, and scorer are accepted
only after materialization_authorization.json exists.

Exact instrument content must not be copied into ActionNet or any development
dataset. Post-score repairs receive a new identity and fresh protected
material.