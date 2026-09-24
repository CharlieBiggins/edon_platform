"""Reproducible seed planning, execution, prediction freezing, and gate summaries."""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path
from typing import Any

from edon.common.hashing import sha256_json


class OrchestrationError(RuntimeError):
    pass


class TrainingOrchestrator:
    def __init__(self, workspace: Path | str):
        self.workspace = Path(workspace)
        self.workspace.mkdir(parents=True, exist_ok=True)

    def prepare_campaign(
        self,
        campaign_id: str,
        actionnet_bundle: dict[str, Any],
        qualification: dict[str, Any],
        seeds: list[int],
        *,
        condition: str,
        command_template: list[str] | None = None,
    ) -> dict[str, Any]:
        if not qualification.get("passed"):
            raise OrchestrationError("training cannot start from an unqualified ActionNet bundle")
        if not seeds or len(seeds) != len(set(seeds)):
            raise OrchestrationError("campaign seeds must be non-empty and unique")
        campaign_dir = self.workspace / campaign_id
        public_dir = campaign_dir / "public"
        protected_dir = campaign_dir / "protected"
        public_dir.mkdir(parents=True, exist_ok=True)
        protected_dir.mkdir(parents=True, exist_ok=True)
        public_dir.chmod(0o755)
        protected_dir.chmod(0o700)
        public_payload = actionnet_bundle["public"]
        protected_payload = actionnet_bundle["protected"]
        (public_dir / "cases.json").write_text(
            json.dumps(public_payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        (protected_dir / "oracle.json").write_text(
            json.dumps(protected_payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        (protected_dir / "oracle.json").chmod(0o600)
        manifest = {
            "schema_version": "edon-training-campaign.v1",
            "campaign_id": campaign_id,
            "condition": condition,
            "seeds": seeds,
            "public_cases_sha256": sha256_json(public_payload),
            "protected_oracle_sha256": sha256_json(protected_payload),
            "qualification_sha256": sha256_json(qualification),
            "command_template": command_template,
            "labels_separated": True,
            "status": "PREPARED",
            "binding_authority": False,
        }
        (campaign_dir / "campaign-manifest.json").write_text(
            json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        return manifest

    def launch_seeds(
        self,
        campaign_id: str,
        command_template: list[str],
        seeds: list[int],
        *,
        execute: bool = False,
        timeout_seconds: int = 86_400,
        environment: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        if not command_template or any(not isinstance(token, str) for token in command_template):
            raise OrchestrationError("command_template must be a non-empty token array")
        campaign_dir = self.workspace / campaign_id
        campaign_dir.mkdir(parents=True, exist_ok=True)
        results: list[dict[str, Any]] = []
        for seed in seeds:
            command = [token.replace("{seed}", str(seed)).replace("{campaign_dir}", str(campaign_dir)) for token in command_template]
            if not execute:
                results.append({"seed": seed, "command": command, "status": "PLANNED"})
                continue
            allowed_environment = {
                "PATH", "PYTHONPATH", "HOME", "LANG", "LC_ALL", "CUDA_VISIBLE_DEVICES",
                "HF_HOME", "TRANSFORMERS_CACHE", "TOKENIZERS_PARALLELISM",
            }
            env = {key: value for key, value in os.environ.items() if key in allowed_environment}
            env.update(environment or {})
            completed = subprocess.run(
                command,
                cwd=campaign_dir,
                env=env,
                capture_output=True,
                text=True,
                timeout=timeout_seconds,
                check=False,
            )
            log = {
                "seed": seed,
                "command": command,
                "returncode": completed.returncode,
                "stdout": completed.stdout,
                "stderr": completed.stderr,
                "status": "COMPLETED" if completed.returncode == 0 else "FAILED",
            }
            (campaign_dir / f"seed-{seed}-execution.json").write_text(
                json.dumps(log, indent=2, sort_keys=True) + "\n", encoding="utf-8"
            )
            results.append({key: value for key, value in log.items() if key not in {"stdout", "stderr"}})
        return {
            "campaign_id": campaign_id,
            "execute": execute,
            "seeds": results,
            "all_completed": bool(results) and all(row["status"] == "COMPLETED" for row in results),
        }

    def freeze_predictions(
        self,
        campaign_id: str,
        seed: int,
        predictions: list[dict[str, Any]],
    ) -> dict[str, Any]:
        case_ids = [row.get("case_id") for row in predictions]
        if not predictions or len(case_ids) != len(set(case_ids)) or any(not case_id for case_id in case_ids):
            raise OrchestrationError("predictions require unique non-empty case IDs")
        campaign_dir = self.workspace / campaign_id
        campaign_dir.mkdir(parents=True, exist_ok=True)
        payload = {"seed": seed, "predictions": predictions, "binding_authority": False}
        output = campaign_dir / f"seed-{seed}-predictions.json"
        output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        manifest = {
            "campaign_id": campaign_id,
            "seed": seed,
            "count": len(predictions),
            "predictions_sha256": sha256_json(payload),
            "path": output.name,
            "frozen": True,
            "binding_authority": False,
        }
        (campaign_dir / f"seed-{seed}-prediction-manifest.json").write_text(
            json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        return manifest

    @staticmethod
    def summarize_gates(campaign_id: str, evaluations: list[dict[str, Any]], required_seeds: list[int]) -> dict[str, Any]:
        by_seed = {int(row["seed"]): row for row in evaluations}
        missing = sorted(set(required_seeds) - set(by_seed))
        seed_passes = {
            str(seed): bool(by_seed.get(seed, {}).get("gate", {}).get("passed"))
            for seed in required_seeds
        }
        passed = not missing and all(seed_passes.values())
        return {
            "schema_version": "edon-training-summary.v1",
            "campaign_id": campaign_id,
            "required_seeds": required_seeds,
            "missing_seeds": missing,
            "seed_passes": seed_passes,
            "passed": passed,
            "status": "CAMPAIGN_GATE_PASSES" if passed else "CAMPAIGN_GATE_FAILS",
            "binding_authority": False,
        }

    @staticmethod
    def reference_oracle_diagnostic(actionnet_bundle: dict[str, Any], seeds: list[int]) -> list[dict[str, Any]]:
        """Exercise custody and scoring plumbing; explicitly not a learned-model run."""

        labels = actionnet_bundle["protected"]["labels"]
        evaluations: list[dict[str, Any]] = []
        for seed in seeds:
            evaluations.append({
                "seed": seed,
                "condition": "REFERENCE_ORACLE_PLUMBING",
                "prediction_count": len(labels),
                "gate": {"passed": True, "checks": {"prediction_count_matches": True}},
                "oracle_derived": True,
                "learning_claim": False,
            })
        return evaluations