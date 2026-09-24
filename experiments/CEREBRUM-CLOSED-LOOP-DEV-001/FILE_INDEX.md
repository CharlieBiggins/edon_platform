# File index

- `config/design.json`: frozen split, profile, renderer, seed, cycle, and safety boundaries.
- `config/learned-gates.json`: future two-seed interactive advancement gates.
- `generate.py`: deterministic episode, turn, oracle, hash, and release materialization.
- `preflight.py`: fail-closed package and hash verification.
- `run_reference.py`: deterministic validation-environment solvability replay.
- `dataset/train-episodes.jsonl`: public training episode specifications.
- `dataset/train-turns.jsonl`: supervised development turns and sample weights.
- `dataset/validation-episodes.jsonl`: held-out development episode specifications.
- `dataset/validation-inputs.jsonl`: label-free teacher-forced diagnostic inputs.
- `oracle/train-oracle.jsonl`: development-only hidden outcome schedules used to generate training traces.
- `oracle/validation-oracle.jsonl`: validation outcome schedules for interactive scoring custody.
- `oracle/validation-labels.jsonl`: separately stored validation turn labels.
- `results/reference-runs.jsonl`: reference episode summaries without turn-level targets.
- `results/qualification-report.json`: generation controls, counts, hashes, and claim boundary.
- `training/training-release.json`: authorized development-only training release.
- `schemas/`: public episode and turn contracts.
- `tests/test_environment.py`: separation, replay, authority rejection, dispatch rejection, and label-isolation tests.