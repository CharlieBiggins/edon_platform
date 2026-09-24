# ACTIONNET-DATA-QUAL-021-PROGRAM

This package creates fresh synthetic supervision for the first native
end-to-end temporal-program experiment. Every example uses the DEV-020
validated `FAMILIAR_AUGMENTED` input interface and targets one constrained
`ACTIONNET_TEMPORAL_PROGRAM_V1`.

The target program lists each event exactly once in canonical order, marks its
execute/defer disposition, claims the resulting state, and claims the derived
non-authoritative certificate. Two independently implemented parsers,
schedulers, transition engines, and evaluators must agree before the dataset is
qualified.

Run `python -u run_campaign.py` to deterministically rematerialize all files.
The splits contain 1,024 training, 128 development-selection, and 256
single-use confirmation trajectories.

Qualification validates synthetic data and executable targets only. It does
not establish model capability, transfer, deployment authority, or IGI.