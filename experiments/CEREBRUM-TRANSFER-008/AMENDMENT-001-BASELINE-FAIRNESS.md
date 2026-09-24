# Amendment 001 — baseline fairness

Effective: 2026-09-01  
Status: `FROZEN_BEFORE_INSTRUMENT_MATERIALIZATION`

This additive amendment preserves the original `CEREBRUM-TRANSFER-008-v1.0.0`
preregistration, reservation, case counts, candidate gates, and Scope-001 hash
anchors. It adds a stricter learned-baseline comparison before any Transfer-008
case, prompt, label, generator, runtime, prediction, or score exists.

## Reason for the amendment

An unmodified base model can fail the strict EDON output interface even when it
has partially correct task reasoning. Comparing C1 only with that raw condition
would mix schema compliance with institutional reasoning and could overstate the
learned contribution.

The raw unmodified base remains required as an end-to-end diagnostic. It is no
longer sufficient by itself for a learned-superiority statement.

## Required conditions

1. `unmodified_base`: the historical raw Qwen condition, without schema-
   constrained decoding. It is diagnostic-only for superiority.
2. `interface_matched_base`: the same unmodified Qwen revision with the shared
   model-agnostic JSON-schema constraint and deterministic compiler used by the
   candidates. It receives no ActionNet training and no demonstrations.
3. `prompted_interface_matched_base`: the interface-matched base plus a frozen,
   public, non-protected interface prompt pack. Demonstrations may teach output
   syntax but may not contain Transfer-008 cases, domains, renderers, mechanism
   instances, timing profiles, predictions, or labels.
4. `transparent_rules_ceiling`: an instrument-side deterministic solvability
   control. It is not a learned baseline and cannot support a learned-model
   superiority claim.
5. The two frozen RB1 candidate seeds, using the same schema constraint,
   compiler, token limits, deterministic decoding, retry budget, hardware
   class, observations, task instructions, and case order as the matched learned
   baselines.

## Primary comparison

For each scored metric, the primary learned comparator is the stronger of
`interface_matched_base` and `prompted_interface_matched_base` on the registered
execution composite. Candidate advancement requires the original frozen gates
and an absolute execution-composite improvement of at least 0.15 over that
strongest eligible matched learned baseline.

The historical improvement-over-raw-base calculation remains reportable, but
it is secondary and cannot be presented as evidence that C1 reasons better than
a fairly interfaced Qwen base.

## Required reporting views

- raw schema validity;
- decision and semantic accuracy conditional on valid raw output;
- final deterministic-compiled accuracy;
- unsafe authorization count and rate;
- transition, post-state, queue, pair, and causal-path metrics;
- token use, generation-limit hits, and retry count;
- the selected strongest matched learned comparator and its selection rule.

No threshold may be changed after instrument or prediction exposure. Any
implementation of this amendment must match `config/baseline-contract.json` and
freeze the learned baseline registry and prompt-pack hash before instrument
materialization is authorized.