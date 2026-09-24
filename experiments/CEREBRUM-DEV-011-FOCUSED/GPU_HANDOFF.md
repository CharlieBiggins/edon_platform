# GPU handoff

The two frozen DEV-010 parent directories must exist at:

```text
CEREBRUM-DEV-010/artifacts/dev010-seed-26090401/
CEREBRUM-DEV-010/artifacts/dev010-seed-26090402/
```

Each directory must contain `final-adapter/` and `training_manifest.json`.
Preflight validates the registered manifest hashes before spending GPU time.

Recommended Modal container allocation:

- one NVIDIA L4 (24 GiB VRAM),
- 4 CPU cores,
- 32 GiB system memory,
- the persistent `edon-dev010` Volume mounted at `/mnt/edon-dev010`,
- exact packages `transformers==5.16.1`, `peft==0.20.0`,
  `bitsandbytes==0.50.2`, and `accelerate==1.10.1`.

From this directory run:

```bash
python preflight.py
python run_focused.py
```

Both training and prediction stages resume from checkpoints. A fully uncached
run is budgeted at roughly 1--2.5 L4 GPU-hours total; actual time depends on
model download/cache state. The run is much smaller than DEV-010: 48 optimizer
steps per parent rather than 252, and 64 predictions per parent rather than 192.

If a cell stops, rerun the same command. Do not add `--restart` unless the
existing continuation checkpoints are intentionally being discarded.

The final focused summary keeps `transfer_authorized=false`. Do not run or
populate CEREBRUM-TRANSFER-010 with these adapters; that frozen reservation was
closed when DEV-010 failed.