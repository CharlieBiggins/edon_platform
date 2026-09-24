# Materialization handoff

Do not begin this handoff until `candidate_registry.json` reports
`CANDIDATES_FROZEN_RB1_PASS_VERIFIED` and `baseline_registry.json` reports
`LEARNED_BASELINES_FROZEN`.

The independent custodian must provide commitments for:

- generator source archive;
- generator and oracle implementation lineages;
- instrument seed;
- label-free input file;
- protected label file;
- overlap-audit report;
- candidate-registry hash;
- baseline-registry and baseline-contract hashes;
- public non-protected interface prompt-pack hash;
- runtime case-order file;
- scoring authorization token or signed approval record.

All learned conditions must share the frozen model revision, observations,
task instructions, hardware class, token limits, deterministic compiler, case
order, and zero-retry policy. The schema-matched track applies the same
model-agnostic schema constraint to Qwen and both C1 candidates. The raw base is
retained as a diagnostic and is not the primary learned comparator.

The shell records hashes and counts only. Protected bytes stay in independent
custody. Materialization must preserve 192 cases, the registered task and pair
allocations, sixteen mechanism floors, and all excluded predecessor lineages.

After commitments are registered, create a new additive instrument artifact and
runtime package. Do not edit the reservation bytes or reuse a prior transfer
generator.