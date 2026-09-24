# CEREBRUM-BUILD-001

`CEREBRUM-BUILD-001` is EDON's engineering-first Cerebrum program. It exists
to build and iterate on a useful institutional-intelligence system without
misrepresenting exploratory development as confirmatory transfer research.

The program is deliberately separate from `CEREBRUM-DEV-009-RB1` and
`CEREBRUM-TRANSFER-008`. Those protocols retain their frozen gates and may be
resumed later. Their results are neither required by nor modified by this build
track.

See [`FILE_INDEX.md`](FILE_INDEX.md) for the complete package and integration
map.

## Implemented now

- an opt-in local Qwen operations provider;
- lazy loading of a Qwen base model and optional PEFT/LoRA adapter;
- deterministic decoding and strict single-object JSON parsing;
- fail-closed abstention when generation is unavailable or malformed, with hard
  rejection of authority-bearing output;
- the existing typed proposal/authority firewall and immutable shadow store;
- an explicit model-lineage requirement;
- a matched-controller benchmark plan;
- a 27-control build-lane readiness preflight.

## Not implemented or demonstrated

- no CEREBRUM-BUILD-001 adapter has been trained;
- no model weights are stored in this repository;
- no build benchmark has been executed or scored;
- no learned end-to-end operations result exists;
- no external, production, real-institution, autonomous-authority, or IGI
  result exists.

## Local runtime

The deterministic provider remains the default. A learned provider must be
enabled explicitly:

```bash
export EDON_CEREBRUM_PROVIDER=qwen
export EDON_CEREBRUM_MODEL=Qwen/Qwen3-4B-Instruct-2507
export EDON_CEREBRUM_ADAPTER=/persistent/models/cerebrum-build-001/final-adapter
export EDON_CEREBRUM_MODEL_LINEAGE=cerebrum-build-001:replace-with-frozen-hash
export EDON_CEREBRUM_LOAD_IN_4BIT=1
export EDON_API_KEY=replace-with-a-random-token-at-least-16-characters

python -m pip install -r experiments/CEREBRUM-BUILD-001/requirements-gpu.txt
PYTHONPATH=src python -m edon.cli serve --state-dir var/cerebrum-build-001
```

Model and adapter paths are deployment inputs, not repository assets. Shadow
cycles remain non-binding regardless of provider selection.

## Checks

```bash
cd edon/experiments/CEREBRUM-BUILD-001
python preflight.py

cd ../../..
PYTHONPATH=edon/src python -m unittest discover \
  -s edon/tests -p 'test_cerebrum_qwen_provider.py' -v
```

Current status: `ENGINEERING_SHELL_READY_MODEL_EXECUTION_NOT_RUN`.

After installing the optional GPU dependencies, test the configured provider
without committing state:

```bash
PYTHONPATH=../../src python run_provider_smoke.py
```