#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent
REPOSITORY = ROOT.parent.parent


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def build_report() -> dict:
    manifest = read_json(ROOT / "manifest.json")
    config = read_json(ROOT / "config" / "build.json")
    benchmark = read_json(ROOT / "config" / "benchmark.json")
    transfer = read_json(ROOT.parent / "CEREBRUM-TRANSFER-008" / "manifest.json")
    provider_source = (REPOSITORY / "src" / "edon" / "cerebrum" / "qwen.py").read_text(
        encoding="utf-8"
    )
    api_source = (REPOSITORY / "src" / "edon" / "api" / "server.py").read_text(
        encoding="utf-8"
    )
    required_docs = [
        "README.md", "PROTOCOL.md", "CLAIMS.md", "BENCHMARK_PLAN.md", "FILE_INDEX.md",
        "TRAINING_HANDOFF.md", "manifest.json", "preflight.py", "run_provider_smoke.py",
        "requirements-gpu.txt",
    ]
    weight_suffixes = {".bin", ".pt", ".pth", ".safetensors", ".ckpt"}
    checks = {
        "required_documents_present": all((ROOT / name).is_file() for name in required_docs),
        "configuration_present": all((ROOT / "config" / name).is_file() for name in ("build.json", "benchmark.json")),
        "artifact_templates_present": all((ROOT / path).is_file() for path in (
            "training/training-release.template.json", "models/model-manifest.template.json"
        )),
        "program_identity": manifest["experiment_id"] == config["program_id"] == "CEREBRUM-BUILD-001",
        "exploratory_status": manifest["status"] == "ENGINEERING_SHELL_READY_MODEL_EXECUTION_NOT_RUN",
        "qwen_base_registered": config["base_model"] == "Qwen/Qwen3-4B-Instruct-2507",
        "training_not_started": manifest["training_started"] is False and config["training"]["started"] is False,
        "no_model_artifact_claim": manifest["model_artifact_exists"] is False,
        "no_model_weights_in_package": not any(path.suffix in weight_suffixes for path in ROOT.rglob("*")),
        "training_release_required": config["training"]["training_release_required"] is True,
        "protected_training_prohibited": config["training"]["protected_labels_allowed"] is False,
        "training_ineligible_records_prohibited": config["training"]["training_ineligible_records_allowed"] is False,
        "shadow_only": config["runtime"]["mode"] == "SHADOW" and config["deployment"]["internal_shadow_only"] is True,
        "fail_closed": config["runtime"]["fail_closed_to_abstain"] is True,
        "explicit_lineage_required": config["runtime"]["model_lineage_required"] is True,
        "kernel_commit_boundary": config["runtime"]["kernel_authorization_required_for_any_commit"] is True,
        "qwen_provider_implemented": all(name in provider_source for name in ("QwenOperationsProvider", "TransformersQwenBackend", "configured_operations_provider")),
        "api_provider_is_configurable": "configured_operations_provider()" in api_source,
        "matched_benchmark_registered": len(benchmark["controller_classes"]) == 6 and "compute_budget" in benchmark["matched_resources"],
        "zero_unsafe_gate": benchmark["absolute_gates"]["unsafe_authorizations_max"] == 0,
        "benchmark_not_executed": manifest["benchmark_executed"] is False and benchmark["status"] == "DESIGN_ONLY_NO_CASES_OR_SCORES",
        "rb1_not_required_for_build": config["research_separation"]["rb1_required_for_build"] is False,
        "transfer008_not_required_for_build": config["research_separation"]["transfer008_required_for_build"] is False,
        "transfer008_unchanged_and_blocked": transfer["status"] == "RESERVED_BLOCKED_PENDING_RB1_TWO_SEED_PASS_AND_INDEPENDENT_INSTRUMENT",
        "transfer008_material_prohibited": config["research_separation"]["may_use_transfer008_material"] is False,
        "no_binding_authority": manifest["binding_authority"] is False and config["binding_authority"] is False and benchmark["binding_authority"] is False,
        "no_external_or_production_authorization": config["deployment"]["external_pilot_authorized"] is False and config["deployment"]["production_authorized"] is False,
    }
    passed = all(checks.values())
    return {
        "schema_version": "cerebrum-build-001-readiness.v1",
        "program_id": "CEREBRUM-BUILD-001",
        "control_count": len(checks),
        "controls_passed": sum(checks.values()),
        "controls": checks,
        "status": "ENGINEERING_SHELL_READY_MODEL_EXECUTION_NOT_RUN" if passed else "BUILD_PREFLIGHT_FAILED",
        "training_authorized": False,
        "model_execution_authorized": True,
        "internal_shadow_authorized": True,
        "external_pilot_authorized": False,
        "production_authorized": False,
        "binding_authority": False,
        "claim_boundary": "Exploratory engineering readiness only; no trained model, benchmark result, transfer result, IGI result, or production authority.",
    }


def main() -> int:
    report = build_report()
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["status"].startswith("ENGINEERING_SHELL_READY") else 1


if __name__ == "__main__":
    raise SystemExit(main())