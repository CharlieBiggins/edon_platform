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
    assert report["core_controls_passed"] == report["core_control_count"] == 34
    assert report["status"] in {
        "READY_PENDING_DEV015_CHECKPOINT12_IMPORT",
        "READY_FOR_DEV016_NARROW_GPU_EXECUTION",
    }
    assert report["expected_optimizer_steps"] == 12
    assert report["expected_development_predictions"] == 128
    assert report["expected_confirmation_predictions_if_selected"] == 192


def test_selector_rejects_nonpassing_and_prefers_post_state() -> None:
    selector = load_module("dev016_selector_test", ROOT / "select_candidate.py")

    def candidate(name: str, step: int, eligible: bool, post_state: float, pivotal: float):
        return {
            "candidate_id": name,
            "step": step,
            "eligible": eligible,
            "metrics": {
                "transition": {"post_state_exact": post_state, "exact_match": post_state},
                "certificate": {"pair_behavior": {"PIVOTAL": {"rate": pivotal}}},
                "queue_trace": {"exact_match": 1.0},
                "pair_contrast": {"exact_match": 1.0},
            },
        }

    rows = [
        candidate("unsafe", 6, False, 1.0, 1.0),
        candidate("lower-state", 6, True, 0.9375, 1.0),
        candidate("higher-state", 12, True, 1.0, 0.9375),
    ]
    selected = selector.choose_candidate(rows)
    assert selected is not None
    assert selected["candidate_id"] == "higher-state"


def test_parent_and_budget_are_frozen() -> None:
    config = json.loads((ROOT / "configs" / "dev016-narrow.json").read_text(encoding="utf-8"))
    assert config["parent_checkpoint_step"] == 12
    assert config["parent_adapter_tree_sha256"] == "sha256:2dd862942bfd21508c18f46cd1d9a67fe5da0e4ef7792860bcd8968ecce8be1a"
    assert config["max_steps"] == 12
    assert config["save_steps"] == 6
    assert config["learning_rate"] == 0.000001
    assert config["task_token_limits"]["TRANSITION"] == 2048


def test_parent_audit_never_reads_confirmation() -> None:
    source = (ROOT / "audit_parent.py").read_text(encoding="utf-8")
    assert "untouched-confirmation" not in source
    assert '"confirmation_accessed": False' in source
    assert 'task == "CERTIFICATE"' in source