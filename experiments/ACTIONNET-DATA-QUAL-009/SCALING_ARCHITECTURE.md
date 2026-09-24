# Scaling architecture

The training split contains 576 counterfactual pairs, 1,152 trajectories, four
renderers, and 16,128 task records. Held-out validation contains 192 pairs, 384
trajectories, one unseen renderer, and 1,344 records.

Scale is concentrated on the failed execution stages rather than on more copies
of the certificate task. Queue targets receive the largest weight, transition
targets the next largest, and pair targets receive dedicated pivotal weighting.
This is a repair instrument, not a scaling-law experiment.