from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(ROOT))
    try:
        spec.loader.exec_module(module)
    finally:
        sys.path.pop(0)
    return module


def test_preflight_core() -> None:
    subprocess.run([sys.executable, "preflight.py", "--allow-missing-parent"], cwd=ROOT, check=True)
    report = json.loads((ROOT / "results" / "readiness-report.json").read_text(encoding="utf-8"))
    assert report["core_controls_passed"] == report["core_control_count"]
    assert report["status"] in {"READY_PENDING_DEV013_SELECTED_ADAPTER_IMPORT", "READY_FOR_DEV015_MIXED_GPU_EXECUTION"}
    assert report["expected_optimizer_steps"] == 24
    assert report["expected_development_predictions"] == 128
    assert report["expected_confirmation_predictions_if_selected"] == 192


def test_selector_rejects_nonpassing_candidates_and_prefers_retention() -> None:
    selector = load_module("dev015_selector_test", ROOT / "select_candidate.py")
    def candidate(name, step, eligible, queue, transition):
        return {
            "candidate_id": name,
            "step": step,
            "eligible": eligible,
            "metrics": {
                "queue_trace": {"exact_match": queue},
                "transition": {"exact_match": transition},
                "certificate": {
                    "decision_accuracy": 1.0,
                    "certificate_mechanism_accuracy": {"UNRESOLVED_APPEAL": {"rate": 1.0}},
                },
                "pair_contrast": {"exact_match": 1.0},
            },
        }
    rows = [
        candidate("unsafe", 6, False, 1.0, 1.0),
        candidate("lower-queue", 12, True, 0.75, 1.0),
        candidate("higher-queue", 18, True, 0.875, 0.75),
    ]
    selected = selector.choose_candidate(rows)
    assert selected is not None
    assert selected["candidate_id"] == "higher-queue"


def test_parent_and_budget_are_frozen() -> None:
    config = json.loads((ROOT / "configs" / "dev015-mixed.json").read_text(encoding="utf-8"))
    assert config["parent_selected_step"] == 6
    assert config["parent_adapter_tree_sha256"] == "sha256:d03460f927a1e3f8fed967fad8f48c5d7fbb2fa77b3898b5a021eb72680f7396"
    assert config["max_steps"] == 24
    assert config["save_steps"] == 12
    assert config["learning_rate"] == 0.000003
    assert config["task_token_limits"]["TRANSITION"] == 2048