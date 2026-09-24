# ACTIONNET-DATA-QUAL-003 Data Design

## Learning units

The successor separates three related tasks rather than requiring one next-token objective to infer all of them implicitly.

### Transition unit

Input:

- typed initial state;
- one observable event with its operand;
- renderer-specific presentation.

Target:

- typed post-event state;
- changed fields;
- applicable failed conditions.

### Certificate unit

Input:

- the same observable state and event sequence.

Target:

- the canonical non-authoritative Cerebrum certificate.

### Pair-contrast unit

Input:

- base and intervention observations sharing a registered pair identity outside the model-facing content.

Target:

- whether the disposition must change;
- the causal field changes;
- both canonical certificates.

## Multi-view policy

Formal, event-log, and memo observations for one trajectory share a semantic trajectory identity in audit metadata but receive distinct model-facing prompts. Split construction occurs before rendering so views of one trajectory cannot cross training and validation boundaries.

Training batches should group or interleave views and pair members without exposing audit identifiers. Renderer-specific accuracy and pivotal sensitivity are mandatory outputs.

## Balance policy

Sampling and loss weighting must prevent base `ALLOW` cases from dominating safety-critical changed outcomes. The frozen release must report counts by:

- decision and semantic state;
- base versus changed variant;
- pair class;
- intervention family;
- renderer;
- task type;
- institution, generator, source, and semantic-family lineage.

No weighting may be selected using public or protected results.

## Leakage policy

The 17 known unsafe cases describe failure families only. Their case IDs, actors, institutions, trajectories, prompts, and exact values cannot be copied into successor training. Repair examples must be newly generated under fresh identities and lineages. The exposed 120-case development set may be reported after candidate selection as a continuity diagnostic, but it is no longer a confirmatory instrument.