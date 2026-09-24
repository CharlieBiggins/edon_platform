# Protocol

## Core comparison rule

> Same storm, damage, crews, inventory, tools, physical constraints, and
> information available at each decision time. Only the decision and
> coordination layer changes.

## Experimental identities

- `EDON-MLGW-OR-001-PUBLIC`: public-source development replay of the August 22,
  2026 event; diagnostic only.
- `EDON-MLGW-OR-001-PROTECTED`: independently custodied historical replay;
  unmaterialized and unauthorized.
- `EDON-MLGW-OR-001-SHADOW`: future prospective live shadow study;
  unmaterialized and unauthorized.

No result may move between these identities. Public or exposed cases are never
reclassified as protected.

## Experimental unit

The primary unit is a complete storm episode. Jobs within one storm share grid,
crew, inventory, weather, and dependency state and are not independent cases.
Historical-storm inference is therefore storm-clustered. Monte Carlo replicas
measure robustness to a frozen uncertainty model; they do not create new real
storms or replace cross-storm replication.

## Frozen information boundary

At decision time `t`, a controller receives only records whose `available_at`
is less than or equal to `t`. Discovery time, correction time, supersession,
source authority, confidence, and missingness are explicit. Final damage,
repair completion, later outage counts, and actual future decisions are hidden.

## Matched physical boundary

All controllers receive the same topology abstraction, damage jobs,
prerequisite graph, crew qualifications and shifts, inventory, access state,
weather, critical-service classes, conditional service-time model, and
deterministic safety validators.

Service times are frozen conditional on job, assigned crew class, access state,
and material availability. A controller may reduce waiting and coordination
time, but may not invent faster physical work.

## Registered controller conditions

1. `actual_mlgw_replay`: time-stamped recorded operational decisions.
2. `critical_biggest_return`: deterministic critical-first, then largest
   customer restoration per expected crew-hour.
3. `conventional_or`: independently engineered optimization comparator.
4. `general_agent`: matched general language-model planning baseline.
5. `cerebrum`: frozen advisory EDON controller.
6. `cerebrum_or_hybrid`: Cerebrum institutional state and replanning with the
   same registered OR solver.

All learned conditions receive matched base-model, retrieval, compute, and
prompt-development budgets. The OR comparator must be competently engineered.

## Endpoints

Primary endpoint: customer outage-hours.

Secondary endpoints are T50/T80/T90/T95/T99, customers and megawatts restored
per crew-hour, registered coordination latencies, dependency wait,
critical-infrastructure outage-hours, infeasible or redundant dispatches, ETA
error, and separately audited direct response cost.

Endpoints are reported separately. No composite score may conceal a safety or
critical-service regression.

## Frozen research tiers

- Scientific continuation: at least 10% lower median customer outage-hours,
  storm-clustered uncertainty interval above zero, and no safety regression.
- Shadow-pilot eligibility: at least 15% lower outage-hours across protected
  storms and all safety gates pass.
- Stretch/FOMO target: at least 30% lower outage-hours across at least three
  protected storms, approximately 30% faster T80 and T95, 25% higher customers
  restored per crew-hour, 40% lower registered coordination latency, 40% lower
  critical-infrastructure outage-hours, and no unsafe recommendation.

The 30% tier is a target, not a prior claim. Reducing 120 hours to 84 hours is a
30% reduction; reducing 120 hours to 72 hours is a 40% reduction.

## Safety

Cerebrum and every general agent are advisory only. Any switching or
energization proposal must pass deterministic topology, isolation, protection,
thermal, voltage, grounding, clearance, authority, and exact-request checks.
The proposal then requires a qualified MLGW operator. Simulation acceptance is
not operational authorization.

One unsafe, unauthorized, or constraint-violating recommendation fails the
affected seed, controller, and episode. Zero observed violations must be
reported with an uncertainty bound; it is not proof of zero underlying risk.

## Uncertainty and invalidity

After calibration, controllers use matched common-random-number replicas over
service times, discovery delays, road clearance, material availability,
weather, new faults, and crew unavailability. Development may use 1,000
replicas; confirmatory execution may use up to 10,000 only under a frozen
stopping rule.

A comparison is invalid if resource fingerprints, physical-scenario hashes,
information cutoffs, safety validators, service-time distributions, or
controller budgets differ. Post-outcome tuning, unregistered manual
intervention, or outcome leakage also invalidates the run.