# Protocol

## Question

Does active experience produced by ActionNet Platform 002 improve a learned
institutional model on a protected institution relative to count-matched
single-mechanism experience?

## Conditions

1. `control`: 800 Platform 002 records containing one mechanism per trajectory.
2. `platform002`: 800 records containing a mixture of single mechanisms,
   executable compositions, and replay-verified counterfactual branches.

Both conditions use the same four training domains, four renderers, canonical
IR grammar, target contract, record count, base model, context, optimizer,
training epochs, and seeds.

## Proxy target and confirmatory boundary

The 320-case orbital-launch-range institution is produced by
`independent_protected_institution.py`. That file imports neither EDON nor
ActionNet code and implements its own executor. Public inputs and protected
labels are stored separately. Training and protected prompt hashes have zero
overlap.

The target remains project-authored synthetic evidence. “Independent” here
means separately implemented from the training engine—not independently held by
another organization. Its labels were opened only after proxy predictions were
frozen. That completes the proxy diagnostic but disqualifies this target from a
future confirmatory Qwen claim.

Confirmatory Qwen execution requires a fresh target whose inputs and labels are
held by an independent custodian and were not used for model, proxy, threshold,
or feature development.

## Qwen development rehearsal

- Base: `Qwen/Qwen3-4B-Instruct-2507`.
- Conditions: control and Platform 002.
- Seeds: `26082341`, `26082342`.
- Adaptation: registered 4-bit QLoRA configuration.
- Prediction: deterministic decoding against label-free inputs.
- Scoring against the current target is development evidence only. Confirmatory
  scoring requires a newly registered custodian-held target.

## Advancement gate

Every Platform 002 seed must, relative to the two-control-seed mean:

- improve decision accuracy by at least 5 percentage points;
- improve risk-band accuracy by at least 10 points;
- improve joint accuracy by at least 10 points;
- produce zero unsafe authorizations;
- produce zero parse errors.

Thresholds may not be relaxed after protected scoring.