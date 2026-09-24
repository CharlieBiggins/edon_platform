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
    assert report["status"] in {
        "READY_PENDING_DEV012_CHECKPOINT_IMPORT",
        "READY_FOR_DEV013_SAFETY_CONSTRAINED_GPU_EXECUTION",
    }
    assert report["expected_optimizer_steps"] == 12
    assert report["expected_development_predictions"] == 96
    assert report["expected_confirmation_predictions_if_selected"] == 64


def test_perfect_predictions_pass_confirmation_gate() -> None:
    prepare = load_module("dev013_prepare_test", ROOT / "prepare_data.py")
    common = load_module("dev013_common_test", ROOT / "dev013_common.py")
    scoring = load_module("dev013_scoring_test", ROOT / "scoring.py")
    prepare.prepare()
    expected = common.read_jsonl(ROOT / "prepared" / "untouched-confirmation-64.jsonl")
    predictions = [{
        "case_id": row["case_id"],
        "parsed": json.loads(row["completion"]),
        "raw_output": row["completion"],
        "confidence": 1.0,
        "ended_with_eos": True,
        "hit_generation_limit": False,
        "generated_token_count": 1,
        "prompt_token_count": 1,
    } for row in expected]
    scorer = scoring.load_scorer()
    result = scorer.score_seed(expected, predictions, scorer.load_evaluator(), common.read_json(common.CONFIG))
    assert result["focused_gate"]["passed"] is True
    assert result["unsafe_authorizations"] == 0


def test_selector_is_safety_first_then_accurate_then_early() -> None:
    selector = load_module("dev013_selector_test", ROOT / "select_candidate.py")
    base = {
        "eligible": True,
        "metrics": {
            "resolved_allow_accuracy": 0.875,
            "paired_boundary_exact": 0.875,
            "decision_accuracy": 0.9375,
        },
    }
    rows = [
        {**base, "candidate_id": "unsafe-best", "step": 12, "eligible": False,
         "metrics": {"resolved_allow_accuracy": 1.0, "paired_boundary_exact": 1.0, "decision_accuracy": 1.0}},
        {**base, "candidate_id": "safe-late", "step": 12},
        {**base, "candidate_id": "safe-early", "step": 6},
    ]
    chosen = selector.choose_candidate(rows)
    assert chosen is not None
    assert chosen["candidate_id"] == "safe-early"


def test_parent_and_budget_are_frozen() -> None:
    config = json.loads((ROOT / "configs" / "dev013-focused.json").read_text(encoding="utf-8"))
    assert config["parent_training_manifest_sha256"] == "sha256:63c35860525c10c5b04f972fb5377072cdd52368ec8bf863262f2007224e321d"
    assert config["parent_checkpoint_step"] == 12
    assert config["max_steps"] == 12
    assert config["save_steps"] == 6
    assert config["learning_rate"] == 0.000005
