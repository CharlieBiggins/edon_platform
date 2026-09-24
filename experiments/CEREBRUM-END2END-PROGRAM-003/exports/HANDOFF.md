# Program-003: tested Modal handoff

Date: September 8, 2026. CPU-qualified only; no GPU job has been launched.

Download `program003-handoff.zip` from this folder and `../restore.py` from the
experiment folder. Upload both into the same notebook working directory on
your attached persistent storage. Keep all Program-001/002 artifacts unchanged.
Use a fresh destination called `program003-workspace`.

Expected bundle SHA-256:
`3e3e8290a82f4a573cddb920f209c07faf079683d2f7edaa467f741dbcfae812`

Expected registration SHA-256:
`27356bf7ad608bdc68e5db46deca1cdcaa5d282b0d8a2d2e2579140a4a269c4e`

Run this setup-only notebook cell:

```python
from pathlib import Path
import hashlib, subprocess, sys

archive = Path("program003-handoff.zip")
assert hashlib.sha256(archive.read_bytes()).hexdigest() == "3e3e8290a82f4a573cddb920f209c07faf079683d2f7edaa467f741dbcfae812"
subprocess.run([
    sys.executable, "restore.py", str(archive), "program003-workspace",
    "--registration-sha256",
    "sha256:27356bf7ad608bdc68e5db46deca1cdcaa5d282b0d8a2d2e2579140a4a269c4e",
], check=True)
experiment = Path("program003-workspace/edon/experiments/CEREBRUM-END2END-PROGRAM-003")
subprocess.run([sys.executable, "-u", "run.py", "runtime"], cwd=experiment, check=True)
```

Runtime checks require the pinned installed packages and one visible CUDA GPU.
They verify both arms with the actual tokenizer and test the tensor loss value
and gradients. If this cell fails, retain the evidence and diagnose the failure;
do not change the config or remove hash checks. No package installation or
Modal volume commit is performed by this setup.

Inspect `results/runtime-readiness.json`: this pilot matches underlying cases
and optimizer steps, NOT token compute. The report gives the trace/control token
exposure ratio. Trace responses are longer than Program-002 responses; wall-time
and GPU memory sufficiency have not been measured locally.

Only after runtime checks pass, start training/development in a separate cell:

```python
subprocess.run([sys.executable, "-u", "run.py", "development"], cwd=experiment, check=True)
```

The runner trains both fresh arms, then generates 128 development responses per
arm and evaluates them. Checkpoints and per-case responses support matching-run
resumption; do not run duplicate cells concurrently.

Read `results/selection.json` when complete. Do not run confirmation on a hold.
Even READY_FOR_CONFIRMATION is eligibility, not a confirmed result or deployment
permission. Confirmation requires a separate explicit user decision.

For a full Prism project ZIP rather than the exact handoff ZIP, use the same
restore command with its filename and the trusted registration hash, without
asserting that a different archive has the handoff ZIP hash. The restore helper
checks each registered source and only recovers a stripped final LF if its
resulting hash is exactly the original. It can regenerate omitted JSONL files.
This recovery path was exercised successfully in a separate CPU workspace.