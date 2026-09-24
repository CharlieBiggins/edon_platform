# Data design

Each record begins with a typed institutional state and an intentionally
unordered event queue. Events are canonically sorted by `(time, priority,
sequence, event_id)`. Events with `time <= decision_clock` execute; later events
are returned in the deferred list without mutating state.

One to three consequential future events are attached to every trajectory.
These include policy denial, conflict assertion, and approval removal, so
executing them accidentally changes the answer. Executed events also mutate
evidence timing and resource reservation on every trajectory. Pivotal,
invariance, and contextual pairs then test whether the model can distinguish
causal changes from ordering, identifier, or already-decisive context changes.

Targets remain compact. State hashes and changed fields are compiled later from
model-predicted states rather than emitted as language-model tokens.