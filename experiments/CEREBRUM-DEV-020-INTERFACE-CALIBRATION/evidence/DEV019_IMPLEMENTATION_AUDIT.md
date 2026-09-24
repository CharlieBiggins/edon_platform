# DEV-019 implementation audit

DEV-019 completed its registered procedure, but the implementation did not
hold the intervention interface sufficiently constant for unique causal
localization.

## Principal findings

- Every condition nested the raw observation inside a new diagnostic packet.
- From B onward, raw and typed event descriptions were both present.
- From C onward, raw events, unordered typed events, ordered typed events, and
  the order identifier list were simultaneously present.
- From D onward, both the initial state and the executed final state were
  present; the field called `predecision_state` was implemented from
  `trajectory["final_state"]`.
- The task continued to request queue execution at every stage.
- The supplied decision was not declared immutable.
- Certificate compilation returned the model's certificate and did not bind or
  preserve supplied support fields.
- The same-schema control compared only packet key sets. Mean prompt size grew
  from 3,773.75 characters in A to 9,185.63 in E.
- The model produced valid JSON and reached EOS, and the predictor would have
  rejected inputs above the registered token limit. Parser failure and literal
  truncation therefore do not explain the main regression.

The largest failure occurred between B and C: 11 decision degradations and 15
exact-certificate degradations. This is consistent with representation and
instruction interference, not evidence that correct event ordering intrinsically
harms the task.

The reproducible machine-readable audit is `dev019-implementation-audit.json`.
