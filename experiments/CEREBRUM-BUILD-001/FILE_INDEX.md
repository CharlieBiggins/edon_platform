# CEREBRUM-BUILD-001 file index

## Program package

| Path | Purpose |
| --- | --- |
| `README.md` | Entry point and local runtime commands |
| `PROTOCOL.md` | Engineering, safety, training, and benchmark boundaries |
| `CLAIMS.md` | Permitted and prohibited claims |
| `BENCHMARK_PLAN.md` | Matched-controller evaluation design |
| `TRAINING_HANDOFF.md` | Requirements for creating the first training release |
| `manifest.json` | Registered Build-001 identity and current disposition |
| `config/build.json` | Runtime, training, research-separation, and deployment controls |
| `config/benchmark.json` | Controller classes, matched resources, tasks, and absolute gates |
| `training/training-release.template.json` | Governed training-release template |
| `models/model-manifest.template.json` | Frozen adapter/model registration template |
| `requirements-gpu.txt` | Optional local Qwen runtime dependencies |
| `preflight.py` | Twenty-seven-control readiness check |
| `run_provider_smoke.py` | One-call, non-binding provider smoke test |
| `tests/test_preflight.py` | Package readiness regression test |

## Integrated EDON files

| Path from `edon/` | Purpose |
| --- | --- |
| `src/edon/cerebrum/qwen.py` | Local Qwen/LoRA backend and provider |
| `src/edon/cerebrum/operations.py` | Typed proposal firewall and nested authority rejection |
| `src/edon/cerebrum/__init__.py` | Public Cerebrum provider exports |
| `src/edon/api/server.py` | Opt-in provider configuration in the shadow service |
| `tests/test_cerebrum_qwen_provider.py` | Provider, grounding, safety, and integration tests |
| `configs/inference/qwen-cerebrum.example.json` | Example learned-provider configuration |
| `docs/architecture/cerebrum.md` | Learned-provider architecture boundary |
| `docs/architecture/kernel-outbox-supervisor.md` | Kernel and shadow integration boundary |
| `docs/platform-operations.md` | Runtime environment configuration |
| `experiments/registry.json` | Canonical Build-001 registration |
| `governance/claim-registry/claims.json` | Build-001 claim boundary |
| `results/summaries/research-status.json` | Current engineering-lane status |

All Build-001 implementation, configuration, documentation, templates, tests,
and status records live inside the `edon/` folder.