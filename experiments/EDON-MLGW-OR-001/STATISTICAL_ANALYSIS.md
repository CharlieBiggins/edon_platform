# Statistical analysis plan

## Primary estimand

Paired percentage change in customer outage-hours between a candidate
controller and the actual-decision replay under the same storm and uncertainty
draw.

## Secondary estimands

T50/T80/T90/T95/T99, customers restored per crew-hour, registered coordination
latencies, dependency wait, critical-service outage-hours, infeasible or
redundant dispatches, ETA error, and direct response cost.

## Pairing and uncertainty

All controllers use common random numbers for each replica. Report paired
differences and ratios. Within-storm replicas are summarized as robustness
distributions. Cross-storm inference treats storm as the cluster and does not
count individual jobs or replicas as independent real-world samples.

## Missingness

- Missing records are never converted to favorable zero values.
- Unknown future information remains unavailable to every controller.
- Unreconstructable actual decisions are reported and may invalidate the
  affected interval.
- Sensitivity analyses use preregistered pessimistic and optimistic bounds.

## Multiplicity and stopping

Customer outage-hours is primary. Safety is a mandatory gate, not a secondary
hypothesis. Other endpoints are reported with family identification and
multiplicity-adjusted intervals where confirmatory claims are made.

The number of storms, seeds, and Monte Carlo replicas is frozen before scoring.
No early stopping based on favorable performance is permitted.